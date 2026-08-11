from django.db import models
from django.conf import settings

class Guest(models.Model):
    ID_TYPE_CHOICES = (
        ('passport', 'Passport'),
        ('national_id', 'National ID / Kebele ID'),
        ('driver_license', 'Driver License'),
        ('other', 'Other Document'),
    )
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='guests',
        blank=True,
        null=True,
        help_text="Primary property associated with this guest record"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='guest_profile'
    )
    full_name = models.CharField(max_length=255, db_index=True)
    phone_number = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(blank=True, null=True)
    id_document_type = models.CharField(max_length=30, choices=ID_TYPE_CHOICES, default='national_id')
    id_document_number = models.CharField(max_length=100, db_index=True)
    id_photo = models.FileField(upload_to='guest_ids/', blank=True, null=True, help_text="Photo / Scan of Guest ID or Passport")
    nationality = models.CharField(max_length=100, default='Ethiopian')
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['full_name', 'phone_number']),
            models.Index(fields=['id_document_number']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.id_document_number})"
