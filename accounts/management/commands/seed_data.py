from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser
from properties.models import Property, PropertyStaff
from subscriptions.models import PropertySubscription
from rooms.models import RoomType, Room
from guests.models import Guest
from bookings.models import Booking
from billing.models import Invoice, InvoiceItem
from payments.models import Transaction
from receipts.models import Receipt
from shifts.models import Shift
from housekeeping.models import HousekeepingTask
from maintenance.models import MaintenanceTicket
from audit.models import AuditLog

class Command(BaseCommand):
    help = 'Seeds initial database records for Guest House Management System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding..."))

        with transaction.atomic():
            # 1. Users
            admin, _ = CustomUser.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@guesthouse.com',
                    'first_name': 'System',
                    'last_name': 'Administrator',
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            admin.set_password('admin123')
            admin.save()

            investor, _ = CustomUser.objects.get_or_create(
                username='investor',
                defaults={
                    'email': 'investor@guesthouse.com',
                    'first_name': 'Abebe',
                    'last_name': 'Bikila',
                    'role': 'investor'
                }
            )
            investor.set_password('investor123')
            investor.save()

            receptionist, _ = CustomUser.objects.get_or_create(
                username='receptionist',
                defaults={
                    'email': 'receptionist@guesthouse.com',
                    'first_name': 'Tigist',
                    'last_name': 'Haile',
                    'role': 'receptionist'
                }
            )
            receptionist.set_password('recep123')
            receptionist.save()

            guest_user, _ = CustomUser.objects.get_or_create(
                username='guest',
                defaults={
                    'email': 'guest@gmail.com',
                    'first_name': 'Dawit',
                    'last_name': 'Kasa',
                    'role': 'guest'
                }
            )
            guest_user.set_password('guest123')
            guest_user.save()

            # 2. Property & Subscription
            prop, _ = Property.objects.get_or_create(
                property_name='Skyline Grand Guest House',
                defaults={
                    'address': 'Bole Atlas Road, Addis Ababa, Ethiopia',
                    'phone': '+251 911 234 567',
                    'email': 'info@skylineguesthouse.com',
                    'investor': investor
                }
            )

            PropertyStaff.objects.get_or_create(
                property=prop,
                user=receptionist,
                defaults={'role': 'receptionist'}
            )

            sub, _ = PropertySubscription.objects.get_or_create(
                property=prop,
                defaults={
                    'investor': investor,
                    'is_trial': True,
                    'is_active': True,
                    'start_date': date.today(),
                    'expiry_date': date.today() + timedelta(days=365)
                }
            )

            # 3. Room Types
            rt_single, _ = RoomType.objects.get_or_create(
                name='Deluxe Single',
                defaults={'capacity': 1, 'default_price': Decimal('1200.00'), 'description': 'Cozy single room with private bathroom'}
            )
            rt_double, _ = RoomType.objects.get_or_create(
                name='Executive Double',
                defaults={'capacity': 2, 'default_price': Decimal('1800.00'), 'description': 'Spacious queen bed with city view balcony'}
            )
            rt_suite, _ = RoomType.objects.get_or_create(
                name='Presidential Suite',
                defaults={'capacity': 4, 'default_price': Decimal('3500.00'), 'description': 'Luxury suite with living room and kitchenette'}
            )

            # 4. Rooms
            rooms_data = [
                ('101', rt_single, Decimal('1200.00'), 'vacant'),
                ('102', rt_single, Decimal('1200.00'), 'occupied'),
                ('103', rt_double, Decimal('1800.00'), 'vacant'),
                ('104', rt_double, Decimal('1800.00'), 'cleaning'),
                ('201', rt_double, Decimal('1800.00'), 'maintenance'),
                ('202', rt_suite, Decimal('3500.00'), 'vacant'),
            ]

            created_rooms = {}
            for num, rt, price, status in rooms_data:
                r, _ = Room.objects.get_or_create(
                    property=prop,
                    room_number=num,
                    defaults={'room_type': rt, 'price_per_night': price, 'status': status}
                )
                created_rooms[num] = r

            # 5. Guests
            g1, _ = Guest.objects.get_or_create(
                id_document_number='ETH-889911',
                defaults={
                    'user': guest_user,
                    'full_name': 'Dawit Kasa',
                    'phone_number': '+251 912 345 678',
                    'email': 'dawit@gmail.com',
                    'id_document_type': 'national_id',
                    'nationality': 'Ethiopian',
                    'address': 'Addis Ababa'
                }
            )

            g2, _ = Guest.objects.get_or_create(
                id_document_number='PASSPORT-P99821',
                defaults={
                    'full_name': 'Sarah Jenkins',
                    'phone_number': '+1 555 019 2831',
                    'email': 'sarah@globaltour.com',
                    'id_document_type': 'passport',
                    'nationality': 'American',
                    'address': 'New York, USA'
                }
            )

            # 6. Active Booking for Room 102
            today = date.today()
            b1, _ = Booking.objects.get_or_create(
                booking_reference='BK-SAMPLE102',
                defaults={
                    'property': prop,
                    'room': created_rooms['102'],
                    'guest': g1,
                    'check_in_date': today - timedelta(days=1),
                    'expected_check_out': today + timedelta(days=2),
                    'number_of_guests': 1,
                    'nightly_rate': Decimal('1200.00'),
                    'amount_paid': Decimal('1200.00'),
                    'status': 'checked_in',
                    'created_by': receptionist
                }
            )

            inv1, _ = Invoice.objects.get_or_create(
                booking=b1,
                defaults={
                    'subtotal': Decimal('3600.00'),
                    'total': Decimal('3600.00'),
                    'amount_paid': Decimal('1200.00'),
                    'status': 'partially_paid'
                }
            )

            InvoiceItem.objects.get_or_create(
                invoice=inv1,
                description='Room Charge (102) - 3 Night(s)',
                defaults={'quantity': 3, 'unit_price': Decimal('1200.00'), 'total': Decimal('3600.00')}
            )

            tx1, _ = Transaction.objects.get_or_create(
                reference_id='TX-SAMPLE01',
                defaults={
                    'property': prop,
                    'booking': b1,
                    'invoice': inv1,
                    'amount': Decimal('1200.00'),
                    'payment_method': 'telebirr',
                    'transaction_status': 'completed',
                    'received_by': receptionist
                }
            )

            Receipt.objects.get_or_create(
                receipt_number='RCP-SAMPLE01',
                defaults={
                    'property': prop,
                    'booking': b1,
                    'transaction': tx1,
                    'guest': g1,
                    'amount_paid': Decimal('1200.00'),
                    'received_by': receptionist
                }
            )

            # 7. Shift for Receptionist
            Shift.objects.get_or_create(
                property=prop,
                receptionist=receptionist,
                status='open',
                defaults={'opening_cash': Decimal('500.00')}
            )

            # 8. Housekeeping Task for Room 104
            HousekeepingTask.objects.get_or_create(
                property=prop,
                room=created_rooms['104'],
                defaults={'task_description': 'Checkout cleaning & bed linen replacement', 'priority': 'high', 'status': 'pending'}
            )

            # 9. Maintenance Ticket for Room 201
            MaintenanceTicket.objects.get_or_create(
                property=prop,
                room=created_rooms['201'],
                defaults={'description': 'Shower plumbing leak repair', 'priority': 'high', 'status': 'open', 'cost': Decimal('450.00'), 'reported_by': receptionist}
            )

            # 10. Audit Log
            AuditLog.log_action(
                user=admin,
                property=prop,
                action='system_seeded',
                new_value='Seeded initial demo data'
            )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded with demo accounts and records!"))
