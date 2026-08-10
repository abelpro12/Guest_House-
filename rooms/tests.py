from decimal import Decimal
from django.test import TestCase
from accounts.models import CustomUser
from properties.models import Property, PropertyStaff
from rooms.models import RoomType, Room

class RoomTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(username='admin_room', password='p', role='admin')
        self.investor = CustomUser.objects.create_user(username='inv_room', password='p', role='investor')
        self.prop = Property.objects.create(property_name='Lodge Room', address='A', phone='1', email='a@a.com', investor=self.investor)
        self.rt = RoomType.objects.create(name='Standard', default_price=Decimal('1000.00'))

    def test_bulk_create_rooms(self):
        self.client.force_login(self.admin)
        
        # Select active property
        self.client.get(f'/properties/select/{self.prop.id}/')
        
        response = self.client.post('/rooms/bulk-create/', {
            'room_type_id': self.rt.id,
            'prefix': '10',
            'start_number': 1,
            'count': 5,
            'price_per_night': '1200.00'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify 5 rooms created: 101, 102, 103, 104, 105
        created_rooms = Room.objects.filter(property=self.prop)
        self.assertEqual(created_rooms.count(), 5)
        self.assertTrue(created_rooms.filter(room_number='101').exists())
        self.assertTrue(created_rooms.filter(room_number='105').exists())
