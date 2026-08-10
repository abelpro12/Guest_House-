from django.db import models
from django.conf import settings
from datetime import date, timedelta
from decimal import Decimal
import builtins

class PropertySubscription(models.Model):
    BILLING_PERIOD_CHOICES = (
        ('monthly', 'Monthly (30 Days)'),
        ('3_months', '3 Months (90 Days)'),
        ('6_months', '6 Months (180 Days)'),
        ('annual', 'Annual (365 Days)'),
    )
    property = models.OneToOneField('properties.Property', on_delete=models.CASCADE, related_name='subscription')
    investor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    is_trial = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(default=date.today)
    expiry_date = models.DateField()
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIOD_CHOICES, default='annual')
    subscription_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('5000.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = self.start_date + timedelta(days=365)
        super().save(*args, **kwargs)

    @builtins.property
    def days_remaining(self):
        delta = self.expiry_date - date.today()
        return max(0, delta.days)

    @builtins.property
    def is_expired(self):
        return date.today() > self.expiry_date or not self.is_active

    def __str__(self):
        status = "TRIAL" if self.is_trial else "ACTIVE"
        return f"{self.property.property_name} ({status} - Fee: {self.subscription_fee} ETB - Expires: {self.expiry_date})"


class SubscriptionTransaction(models.Model):
    subscription = models.ForeignKey(PropertySubscription, on_delete=models.CASCADE, related_name='transactions')
    tx_ref = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='ETB')
    status = models.CharField(max_length=20, default='pending') # pending, completed, failed
    chapa_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SubTx {self.tx_ref} - {self.amount} {self.currency} ({self.status})"
