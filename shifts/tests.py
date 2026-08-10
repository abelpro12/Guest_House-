from decimal import Decimal
from django.test import TestCase
from accounts.models import CustomUser
from properties.models import Property
from shifts.models import Shift

class ShiftTests(TestCase):
    def setUp(self):
        self.investor = CustomUser.objects.create_user(username='inv_shift', password='p', role='investor')
        self.receptionist = CustomUser.objects.create_user(username='recep_shift', password='p', role='receptionist')
        self.prop = Property.objects.create(property_name='Lodge Shift', address='A', phone='1', email='a@a.com', investor=self.investor)

    def test_start_and_close_shift(self):
        shift = Shift.objects.create(
            property=self.prop,
            receptionist=self.receptionist,
            opening_cash=Decimal('500.00'),
            status='open'
        )

        self.assertEqual(shift.status, 'open')
        shift.close_shift(Decimal('500.00'))

        self.assertEqual(shift.status, 'closed')
        self.assertEqual(shift.difference, Decimal('0.00'))
