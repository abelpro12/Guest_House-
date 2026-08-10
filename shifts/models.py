from django.db import models
from django.conf import settings
from django.db.models import Sum
from decimal import Decimal
from payments.models import Transaction

class Shift(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('closed', 'Closed'),
    )
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='shifts')
    receptionist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shifts')
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    expected_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    actual_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    difference = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    def calculate_expected_cash(self):
        """Calculates expected cash: opening cash + cash transactions created during this shift."""
        end = self.end_time or models.functions.Now()
        cash_total = Transaction.objects.filter(
            property=self.property,
            received_by=self.receptionist,
            payment_method='cash',
            transaction_status='completed',
            timestamp__gte=self.start_time,
            timestamp__lte=end
        ).aggregate(total=Sum('amount'))['total'] or 0.00
        return self.opening_cash + Decimal(str(cash_total))

    def close_shift(self, actual_cash_amount):
        from django.utils import timezone
        self.end_time = timezone.now()
        self.expected_cash = self.calculate_expected_cash()
        self.actual_cash = Decimal(str(actual_cash_amount))
        self.difference = self.actual_cash - self.expected_cash
        self.status = 'closed'
        self.save()

    def __str__(self):
        return f"Shift #{self.id} - {self.receptionist.username} ({self.get_status_display()})"
