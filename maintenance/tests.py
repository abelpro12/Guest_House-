from decimal import Decimal
from django.test import TestCase
from accounts.models import CustomUser
from properties.models import Property
from rooms.models import RoomType, Room
from maintenance.models import MaintenanceTicket

class MaintenanceTests(TestCase):
    def setUp(self):
        self.investor = CustomUser.objects.create_user(username='inv_m', password='p', role='investor')
        self.prop = Property.objects.create(property_name='Lodge M', address='A', phone='1', email='a@a.com', investor=self.investor)
        self.rt = RoomType.objects.create(name='Standard', default_price=Decimal('1000.00'))
        self.room = Room.objects.create(property=self.prop, room_number='301', room_type=self.rt, price_per_night=Decimal('1000.00'), status='vacant')

    def test_maintenance_ticket_locks_and_unlocks_room(self):
        # Create ticket
        self.room.status = 'maintenance'
        self.room.save()

        ticket = MaintenanceTicket.objects.create(
            property=self.prop,
            room=self.room,
            description='Pipe leak',
            priority='high',
            status='open'
        )

        self.assertEqual(ticket.room.status, 'maintenance')

        # Resolve ticket
        ticket.status = 'resolved'
        ticket.save()
        self.room.status = 'vacant'
        self.room.save()

        self.assertEqual(self.room.status, 'vacant')
