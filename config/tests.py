from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from properties.models import Property, PropertyStaff
from rooms.models import Room, RoomType
from guests.models import Guest
from bookings.models import Booking

class SecurityAndPermissionsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(username='admin_test', password='password123', role='admin')
        self.investor = CustomUser.objects.create_user(username='investor_test', password='password123', role='investor')
        self.receptionist = CustomUser.objects.create_user(username='recep_test', password='password123', role='receptionist')
        self.guest_user = CustomUser.objects.create_user(username='guest_test', password='password123', role='guest')

        self.property = Property.objects.create(
            property_name='Test Hotel',
            address='Addis Ababa',
            phone='+251911000000',
            email='test@hotel.com',
            investor=self.investor,
            tin_number='1234567890',
            vat_rate=Decimal('15.00'),
            tot_rate=Decimal('2.00')
        )

        PropertyStaff.objects.create(
            property=self.property,
            user=self.receptionist,
            role='receptionist',
            base_salary=Decimal('5000.00')
        )

        self.room_type = RoomType.objects.create(name='Standard', default_price=Decimal('1000.00'))
        self.room = Room.objects.create(
            property=self.property,
            room_number='101',
            room_type=self.room_type,
            price_per_night=Decimal('1000.00'),
            status='vacant'
        )

        self.guest = Guest.objects.create(
            property=self.property,
            full_name='Abebe Bikila',
            phone_number='+251912345678',
            id_document_number='ID98765'
        )

    def test_receptionist_cannot_access_reports(self):
        self.client.login(username='recep_test', password='password123')
        response = self.client.get(reverse('reports:index'))
        self.assertEqual(response.status_code, 302) # Redirected due to @investor_or_admin_required

    def test_investor_can_access_reports(self):
        self.client.login(username='investor_test', password='password123')
        session = self.client.session
        session['selected_property_id'] = self.property.id
        session.save()
        response = self.client.get(reverse('reports:index'))
        self.assertEqual(response.status_code, 200)

    def test_reservation_calendar_view(self):
        self.client.login(username='recep_test', password='password123')
        session = self.client.session
        session['selected_property_id'] = self.property.id
        session.save()
        response = self.client.get(reverse('bookings:calendar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Room 101')

    def test_guest_creation_with_property_association(self):
        self.client.login(username='recep_test', password='password123')
        session = self.client.session
        session['selected_property_id'] = self.property.id
        session.save()
        response = self.client.post(reverse('guests:create'), {
            'full_name': 'Tilahun Gessesse',
            'phone_number': '+251922334455',
            'id_document_type': 'national_id',
            'id_document_number': 'ID554433',
            'nationality': 'Ethiopian'
        })
        self.assertEqual(response.status_code, 302)
        new_guest = Guest.objects.get(phone_number='+251922334455')
        self.assertEqual(new_guest.property, self.property)
