import math
import datetime
import os
from io import BytesIO

from django.db import models
from django.db.models import Q
from django.core.files import File
from django.apps import apps
from django.utils import timezone
from django_enumfield import enum
from django.contrib.auth.models import User
from django.urls import reverse

from PIL import Image
from swaps.model_enums import SwapStatus
from sizes.models import Size
from sizes.model_enums import GenderOptions
from .model_enums import ProductStatus, ClothingType

# Create your models here.
class Product(models.Model):

    name = models.CharField(max_length=50)
    description = models.TextField(max_length=250)
    gender = enum.EnumField(GenderOptions, default=GenderOptions.UNISEX)
    clothing_type = enum.EnumField(ClothingType, default=ClothingType.T_SHIRT)
    size = models.ForeignKey(Size, null=True, on_delete=models.SET_NULL)
    image = models.ImageField(upload_to='product_pics')
    image2 = models.ImageField(upload_to='product_pics', blank=True)
    image3 = models.ImageField(upload_to='product_pics', blank=True)
    image4 = models.ImageField(upload_to='product_pics', blank=True)
    date_posted = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    status = enum.EnumField(ProductStatus, default=ProductStatus.LIVE)

    # Will store image crop dims - filled in ProductCreateView Form
    crop_dimensions_image = None
    crop_dimensions_image2 = None
    crop_dimensions_image3 = None
    crop_dimensions_image4 = None

    def __str__(self):
        return f'ID: {self.id} - {self.name} - status:{self.status.name}'

    def get_absolute_url(self):
        return reverse('product-detail', kwargs={'pk': self.pk})

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # FIXME will the lines below cause issues if we update the product??
        self.image = self.crop_resize_rename_image(self.image, self.crop_dimensions_image, 'image')
        self.image2 = self.crop_resize_rename_image(self.image2, self.crop_dimensions_image2, 'image2')
        self.image3 = self.crop_resize_rename_image(self.image3, self.crop_dimensions_image3, 'image3')
        self.image4 = self.crop_resize_rename_image(self.image4, self.crop_dimensions_image4, 'image4')
        super(Product, self).save(force_insert=False, force_update=False, using=None, update_fields=None)

    def crop_resize_rename_image(self, img_field, crop_dimensions, output_filename_prefix):

        if (not bool(img_field)) or (crop_dimensions is None):
            return img_field  # TODO probably log here if img is not None but crop dims are

        pil_img = Image.open(img_field)
        img_format = pil_img.format  # note - important this comes above rotation

        # Rotate mobile upload images that otherwise get wrong orientation
        exif = pil_img._getexif()
        orientation_key = 274  # cf ExifTags
        if exif and orientation_key in exif:
            orientation = exif[orientation_key]
            rotate_values = {
                3: Image.ROTATE_180,
                6: Image.ROTATE_270,
                8: Image.ROTATE_90
            }
            if orientation in rotate_values:
                pil_img = pil_img.transpose(rotate_values[orientation])

        pil_img = pil_img.crop(crop_dimensions)  # crop image
        pil_img = pil_img.resize((512, 512))  # resize image
        thumb_io = BytesIO()  # create a BytesIO object
        pil_img.save(thumb_io, img_format)  # save image to BytesIO object

        _, file_extension = os.path.splitext(self.image.name)
        new_filename = self.date_posted.strftime(f'{output_filename_prefix}_%d_%m_%Y_%H_%M_%S{file_extension}')
        image = File(thumb_io, name=new_filename)  # create a django friendly File object

        return image

    @property
    def number_of_offers(self):
        """ Returns number of pending offers currently for this product

        Note - using apps.get_model() to avoid circular import
        """
        Swap = apps.get_model('swaps', 'Swap')
        return len(Swap.objects.filter(desired_product=self, status=SwapStatus.PENDING_REVIEW))

    @property
    def hours_left_to_checkout(self):
        """ Returns the time left to complete checkout of this product before status automatically reverts back to
        LIVE and the Swap gets cancelled
        """
        Swap = apps.get_model('swaps', 'Swap')
        hours_left_to_checkout = None
        if self.status == ProductStatus.PENDING_CHECKOUT:
            swap = Swap.objects.get((Q(offered_product=self) | Q(desired_product=self))
                                    & Q(status=SwapStatus.PENDING_CHECKOUT))
            hours_left_to_checkout = swap.hours_left_to_checkout
        return hours_left_to_checkout

