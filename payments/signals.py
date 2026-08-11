from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction
from notifications.models import Notification

@receiver(post_save, sender=Transaction)
def create_transaction_notification(sender, instance, created, **kwargs):
    if created and instance.transaction_status == 'completed':
        title = f"Payment Received: {instance.amount} ETB"
        message = f"Transaction #{instance.reference_id} received via {instance.get_payment_method_display()} for Booking {instance.booking.booking_reference}."
        Notification.notify_property_investors_and_admins(
            property=instance.property,
            title=title,
            message=message
        )
