import uuid
from django.db import models
from django.conf import settings

class Transaction(models.Model):
    METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('telebirr', 'Telebirr'),
        ('cbe_birr', 'CBE Birr'),
        ('bank_transfer', 'Bank Transfer'),
        ('chapa', 'Chapa Gateway'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('voided', 'Voided'),
    )

    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='transactions')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='transactions')
    invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=METHOD_CHOICES, default='cash')
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_id} - {self.amount} ETB via {self.get_payment_method_display()} ({self.get_transaction_status_display()})"
