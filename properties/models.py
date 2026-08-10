from django.db import models
from django.conf import settings

class Property(models.Model):
    property_name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_properties'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Properties'

    def __str__(self):
        return self.property_name


class PropertyStaff(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='property_assignments')
    role = models.CharField(max_length=50, default='receptionist')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('property', 'user')

    def __str__(self):
        return f"{self.user.username} @ {self.property.property_name} ({self.role})"
