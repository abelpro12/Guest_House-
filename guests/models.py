from django.db import models
from django.conf import settings

class Guest(models.Model):
    ID_TYPE_CHOICES = (
        ('passport', 'Passport'),
        ('national_id', 'National ID / Kebele ID'),
        ('driver_license', 'Driver License'),
        ('other', 'Other Document'),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='guest_profile'
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    id_document_type = models.CharField(max_length=30, choices=ID_TYPE_CHOICES, default='national_id')
    id_document_number = models.CharField(max_length=100)
    nationality = models.CharField(max_length=100, default='Ethiopian')
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.id_document_number})"
