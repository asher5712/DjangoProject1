from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from users.validators import is_in_chichester


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(widget=forms.TextInput(attrs={'placeholder': 'email'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'username'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'confirm password'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        exclude = ['user']

    def __init__(self, *args, **kwargs):
        super(UserRegisterForm, self).__init__(*args, **kwargs)
        for fieldname in ['username', 'email', 'password1', 'password2']:
            self.fields[fieldname].help_text = None


class UserPostcodeForm(forms.ModelForm):
    postcode = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'postcode'}),
                               validators=[is_in_chichester])

    class Meta:
        model = Profile
        fields = ['postcode']


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'password'}))


class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['username', 'email']


class ProfileUpdateForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['image', 'bio']

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        for fieldname in ['image', 'bio']:
            self.fields[fieldname].help_text = None

    def save(self, commit=True):
        self.instance.crop_dimensions_image = self.extract_crop_dims_from_post_data('crop_dimensions_image')
        return super(ProfileUpdateForm, self).save(commit=True)

    def extract_crop_dims_from_post_data(self, field_name):
        try:
            dims = [int(dim) for dim in self.data.get(field_name).split(',')]
        except ValueError:
            dims = None  # means no image was uploaded for this field
        return dims


class ShippingAddressUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ['image', 'bio', 'user', 'gender_preference', 'sizes']  # ie include all fields except image (house_name_number, address...)
        labels = {'house_name_number': 'House Name/Number',  # django automates this. override bad ones.
                  'address_line_1': 'Address Line 1',
                  'address_line_2': 'Address Line 2',
                  'town_city': 'Town/City',
                  'contact_number': 'Contact Number'
                  }

    def __init__(self, *args, **kwargs):
        super(ShippingAddressUpdateForm, self).__init__(*args, **kwargs)
        self.fields['house_name_number'].required = True
        self.fields['address_line_1'].required = True
        self.fields['town_city'].required = True
        self.fields['postcode'].required = True
        self.fields['contact_number'].required = True

    def is_initial_valid(self):
        """
        Returns True if initial values passed into form are already valid.

        Used to determine whether or not we need to redirect user to shipping address form after a match.

        Returns
        -------
        is_valid: bool
        """
        try:
            for field_name, field in self.fields.items():
                field.validate(value=self.initial.get(field_name))
        except ValidationError:
            return False

        return True
