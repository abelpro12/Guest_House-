from django.db import models

class RoomType(models.Model):
    name = models.CharField(max_length=100) # e.g. Single, Double, Deluxe, Suite
    description = models.TextField(blank=True, null=True)
    capacity = models.PositiveIntegerField(default=2)
    default_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} (Cap: {self.capacity})"


class Room(models.Model):
    STATUS_CHOICES = (
        ('vacant', 'Vacant / Ready'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning / Housekeeping'),
        ('maintenance', 'Maintenance'),
        ('unavailable', 'Unavailable'),
    )
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=50)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms')
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='vacant')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('property', 'room_number')
        ordering = ['room_number']

    def __str__(self):
        return f"Room {self.room_number} - {self.room_type.name} ({self.get_status_display()})"
