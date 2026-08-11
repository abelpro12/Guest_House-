import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )

    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey('rooms.Room', on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey('guests.Guest', on_delete=models.CASCADE, related_name='bookings')
    booking_reference = models.CharField(max_length=20, unique=True, editable=False)
    
    check_in_date = models.DateField()
    check_in_time = models.TimeField(blank=True, null=True)
    expected_check_out = models.DateField()
    actual_check_out = models.DateTimeField(blank=True, null=True)
    
    number_of_guests = models.PositiveIntegerField(default=1)
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    special_requests = models.TextField(blank=True, null=True, help_text="Special requests or internal booking notes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['room', 'check_in_date', 'expected_check_out']),
            models.Index(fields=['booking_reference']),
        ]

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = f"BK-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate nights and total amount
        nights = max(1, (self.expected_check_out - self.check_in_date).days)
        self.total_amount = Decimal(str(self.nightly_rate)) * nights
        self.amount_paid = Decimal(str(self.amount_paid))
        self.balance = self.total_amount - self.amount_paid
        super().save(*args, **kwargs)

    @classmethod
    def check_overlap(cls, room, check_in, check_out, exclude_booking_id=None):
        """
        Returns True if an active booking overlaps with [check_in, check_out].
        Active statuses: 'confirmed', 'checked_in'.
        """
        qs = cls.objects.filter(
            room=room,
            status__in=['confirmed', 'checked_in'],
            check_in_date__lt=check_out,
            expected_check_out__gt=check_in
        )
        if exclude_booking_id:
            qs = qs.exclude(id=exclude_booking_id)
        return qs.exists()

    def __str__(self):
        return f"Ref: {self.booking_reference} | Room {self.room.room_number} - {self.guest.full_name} ({self.get_status_display()})"
