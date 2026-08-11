from django.db import models
from django.conf import settings

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def notify(cls, user, title, message, property=None):
        return cls.objects.create(
            user=user,
            property=property,
            title=title,
            message=message
        )

    @classmethod
    def notify_property_investors_and_admins(cls, property, title, message):
        from accounts.models import CustomUser
        users = CustomUser.objects.filter(models.Q(role='admin') | models.Q(id=property.investor_id)).distinct()
        notifications = [
            cls(user=user, property=property, title=title, message=message)
            for user in users
        ]
        return cls.objects.bulk_create(notifications)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
