import uuid
from django.db import models
from django.conf import settings

class Receipt(models.Model):
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='receipts')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='receipts')
    transaction = models.ForeignKey('payments.Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='receipts')
    guest = models.ForeignKey('guests.Guest', on_delete=models.CASCADE, related_name='receipts')
    
    receipt_number = models.CharField(max_length=50, unique=True, editable=False)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    is_voided = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True, null=True)
    
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        status = "VOIDED" if self.is_voided else "VALID"
        return f"Receipt #{self.receipt_number} - {self.amount_paid} ETB ({status})"
