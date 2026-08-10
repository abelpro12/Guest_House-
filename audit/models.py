from django.db import models
from django.conf import settings
from config.middleware import get_current_request

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    property = models.ForeignKey('properties.Property', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100) # e.g. login, create_booking, void_receipt, price_change
    model_name = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    @classmethod
    def log_action(cls, user, property, action, model_name=None, object_id=None, old_value=None, new_value=None):
        req = get_current_request()
        ip = None
        if req:
            ip = req.META.get('HTTP_X_FORWARDED_FOR', req.META.get('REMOTE_ADDR'))
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()

        return cls.objects.create(
            user=user,
            property=property,
            action=action,
            model_name=model_name,
            object_id=object_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip
        )

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.action} ({self.model_name})"
