from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Platform Admin'),
        ('investor', 'Investor / Owner'),
        ('accountant', 'Finance / Accountant'),
        ('receptionist', 'Front Desk Receptionist'),
        ('guest', 'Guest / Customer'),
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_investor(self):
        return self.role == 'investor'

    @property
    def is_accountant(self):
        return self.role == 'accountant'

    @property
    def is_receptionist(self):
        return self.role == 'receptionist'

    @property
    def is_guest(self):
        return self.role == 'guest'
