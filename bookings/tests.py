from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from accounts.models import CustomUser
from properties.models import Property, PropertyStaff
from rooms.models import RoomType, Room
from guests.models import Guest
from bookings.models import Booking
from billing.models import Invoice, InvoiceItem

class BookingOverlapTests(TestCase):
    def setUp(self):
        self.investor = CustomUser.objects.create_user(username='inv', password='p', role='investor')
        self.receptionist = CustomUser.objects.create_user(username='recep', password='p', role='receptionist')
        self.prop = Property.objects.create(property_name='Lodge', address='Addr', phone='123', email='a@a.com', investor=self.investor)
        PropertyStaff.objects.create(property=self.prop, user=self.receptionist, role='receptionist')
        self.rt = RoomType.objects.create(name='Standard', default_price=Decimal('1000.00'))
        self.room = Room.objects.create(property=self.prop, room_number='101', room_type=self.rt, price_per_night=Decimal('1000.00'), status='vacant')
        self.guest = Guest.objects.create(full_name='Abebe', phone_number='0911', id_document_number='ID123')

    def test_overlap_prevention(self):
        today = date.today()
        b1 = Booking.objects.create(
            property=self.prop,
            room=self.room,
            guest=self.guest,
            check_in_date=today,
            expected_check_out=today + timedelta(days=3),
            nightly_rate=Decimal('1000.00'),
            status='confirmed'
        )

        has_overlap = Booking.check_overlap(self.room, today + timedelta(days=1), today + timedelta(days=4))
        self.assertTrue(has_overlap)

        no_overlap = Booking.check_overlap(self.room, today + timedelta(days=4), today + timedelta(days=6))
        self.assertFalse(no_overlap)

    def test_quick_check_in_workflow(self):
        self.client.force_login(self.receptionist)
        response = self.client.post('/bookings/quick-check-in/', {
            'room_id': self.room.id,
            'guest_id': self.guest.id,
            'nights': 2,
            'initial_payment': '500.00',
            'payment_method': 'cash'
        })
        self.assertEqual(response.status_code, 302)
        
        booking = Booking.objects.filter(room=self.room, status='checked_in').first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.amount_paid, Decimal('500.00'))
        
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'occupied')

    def test_check_in_and_check_out_confirmed_booking(self):
        today = date.today()
        booking = Booking.objects.create(
            property=self.prop,
            room=self.room,
            guest=self.guest,
            check_in_date=today,
            expected_check_out=today + timedelta(days=2),
            nightly_rate=Decimal('1000.00'),
            status='confirmed'
        )
        invoice = Invoice.objects.create(
            booking=booking,
            subtotal=Decimal('2000.00'),
            total=Decimal('2000.00'),
            amount_paid=Decimal('0.00'),
            balance=Decimal('2000.00')
        )
        InvoiceItem.objects.create(invoice=invoice, description='Room Charge', quantity=2, unit_price=Decimal('1000.00'), total=Decimal('2000.00'))

        self.client.force_login(self.receptionist)
        
        # 1. Test explicit check-in
        res1 = self.client.get(f'/bookings/{booking.id}/check-in/')
        self.assertEqual(res1.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'checked_in')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'occupied')

        # 2. Test checkout
        res2 = self.client.post(f'/bookings/{booking.id}/check-out/', {
            'extra_charge_amount': '0.00',
            'discount_amount': '0.00',
            'tax_amount': '0.00',
            'final_payment': '2000.00',
            'payment_method': 'cash'
        })
        self.assertEqual(res2.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'checked_out')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'cleaning')
