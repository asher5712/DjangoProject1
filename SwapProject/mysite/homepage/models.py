from django.db import models
from django.utils import timezone

# Create your models here.
class PotentialUser(models.Model):

    email = models.EmailField()
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.email
