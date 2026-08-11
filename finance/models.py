from django.db import models
from django.conf import settings
from properties.models import Property
from maintenance.models import MaintenanceTicket
from decimal import Decimal

class Expense(models.Model):
    CATEGORY_CHOICES = (
        ('maintenance', '🛠️ Maintenance & Repairs'),
        ('utilities', '⚡ Utilities & Fuel'),
        ('supplies', '🧹 Housekeeping & Cleaning Supplies'),
        ('amenities', '🍱 Amenities & Guest Supplies'),
        ('payroll', '💼 Salaries & Staff Wages'),
        ('taxes', '🏛️ Taxes & Government Licensing'),
        ('other', '📦 Other Operational Expense'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash Drawer'),
        ('bank_transfer', 'Bank Transfer (CBE / Dashen / Awash)'),
        ('telebirr', 'Telebirr'),
        ('cbe_birr', 'CBE Birr'),
        ('other', 'Other'),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='expenses')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    paid_to = models.CharField(max_length=255, blank=True, null=True, help_text="Vendor / Recipient Name")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='cash')
    maintenance_ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.SET_NULL, blank=True, null=True, related_name='expenses')
    receipt_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Invoice or Receipt #")
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount} ETB ({self.get_category_display()})"


class StaffPayroll(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft / Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='payrolls')
    staff_member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payrolls')
    period_name = models.CharField(max_length=50, help_text="e.g. August 2026")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Income Tax / Pension")
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    paid_on = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.net_salary = (self.base_salary + self.bonus) - (self.deductions + self.tax_deduction)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff_member.get_full_name() or self.staff_member.username} — {self.period_name} ({self.net_salary} ETB)"


class StaffAttendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present 🟢'),
        ('absent', 'Absent 🔴'),
        ('half_day', 'Half Day 🟡'),
        ('late', 'Late ⏳'),
        ('leave', 'On Leave 🏖️'),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='attendances')
    staff_member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('staff_member', 'date')

    def __str__(self):
        return f"{self.staff_member.username} on {self.date}: {self.get_status_display()}"
