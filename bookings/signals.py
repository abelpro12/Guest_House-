from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from notifications.models import Notification

@receiver(post_save, sender=Booking)
def create_booking_notification(sender, instance, created, **kwargs):
    if created:
        title = f"New Reservation: {instance.booking_reference}"
        message = f"Booking confirmed for {instance.guest.full_name} in Room {instance.room.room_number} from {instance.check_in_date} to {instance.expected_check_out}."
        Notification.notify_property_investors_and_admins(
            property=instance.property,
            title=title,
            message=message
        )
