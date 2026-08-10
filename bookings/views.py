from datetime import datetime, date, timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse

from .models import Booking
from rooms.models import Room
from guests.models import Guest
from billing.models import Invoice, InvoiceItem
from payments.models import Transaction
from receipts.models import Receipt
from audit.models import AuditLog

@login_required
def booking_list(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Please select a property.")
        return redirect('properties:list')

    bookings = Booking.objects.filter(property=prop).select_related('room', 'guest').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    return render(request, 'bookings/booking_list.html', {
        'bookings': bookings,
        'current_status': status_filter
    })

@login_required
def booking_create(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Please select a property.")
        return redirect('properties:list')

    rooms = Room.objects.filter(property=prop, is_active=True)
    guests = Guest.objects.all().order_by('-created_at')

    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        guest_id = request.POST.get('guest_id')
        check_in_str = request.POST.get('check_in_date')
        check_out_str = request.POST.get('expected_check_out')
        num_guests = int(request.POST.get('number_of_guests', 1))
        initial_payment = Decimal(request.POST.get('initial_payment', '0.00'))
        payment_method = request.POST.get('payment_method', 'cash')

        room = get_object_or_404(Room, id=room_id, property=prop)
        guest = get_object_or_404(Guest, id=guest_id)

        check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        expected_check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

        if check_in_date >= expected_check_out:
            messages.error(request, "Check-out date must be after check-in date.")
            return render(request, 'bookings/booking_form.html', {'rooms': rooms, 'guests': guests})

        # Overlap Validation
        if Booking.check_overlap(room, check_in_date, expected_check_out):
            messages.error(request, f"Room {room.room_number} is already booked for the selected dates.")
            return render(request, 'bookings/booking_form.html', {'rooms': rooms, 'guests': guests})

        with transaction.atomic():
            booking = Booking.objects.create(
                property=prop,
                room=room,
                guest=guest,
                check_in_date=check_in_date,
                expected_check_out=expected_check_out,
                number_of_guests=num_guests,
                nightly_rate=room.price_per_night,
                amount_paid=initial_payment,
                status='confirmed',
                created_by=request.user
            )

            # Create Invoice
            invoice = Invoice.objects.create(
                booking=booking,
                subtotal=booking.total_amount,
                tax=0,
                discount=0,
                total=booking.total_amount,
                amount_paid=initial_payment,
                balance=booking.balance,
                status='paid' if booking.balance <= 0 else ('partially_paid' if initial_payment > 0 else 'unpaid')
            )

            # Invoice item for room charge
            nights = (expected_check_out - check_in_date).days or 1
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f"Room Charge ({room.room_number}) - {nights} Night(s)",
                quantity=nights,
                unit_price=room.price_per_night,
                total=booking.total_amount
            )

            if initial_payment > 0:
                Transaction.objects.create(
                    property=prop,
                    booking=booking,
                    invoice=invoice,
                    amount=initial_payment,
                    payment_method=payment_method,
                    transaction_status='completed',
                    received_by=request.user
                )

            # Log audit
            AuditLog.log_action(
                user=request.user,
                property=prop,
                action='create_booking',
                model_name='Booking',
                object_id=str(booking.id),
                new_value=booking.booking_reference
            )

        messages.success(request, f"Booking {booking.booking_reference} created successfully!")
        return redirect('bookings:detail', booking_id=booking.id)

    return render(request, 'bookings/booking_form.html', {'rooms': rooms, 'guests': guests})


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    invoice = getattr(booking, 'invoice', None)
    transactions = booking.transactions.all().order_by('-timestamp')
    receipts = booking.receipts.all().order_by('-created_at')

    return render(request, 'bookings/booking_detail.html', {
        'booking': booking,
        'invoice': invoice,
        'transactions': transactions,
        'receipts': receipts
    })


@login_required
def quick_check_in(request, booking_id=None):
    """Executes Quick Check-In workflow atomically."""
    prop = getattr(request, 'current_property', None)
    
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        guest_id = request.POST.get('guest_id')
        num_nights = int(request.POST.get('nights', 1))
        initial_payment = Decimal(request.POST.get('initial_payment', '0.00'))
        payment_method = request.POST.get('payment_method', 'cash')

        room = get_object_or_404(Room, id=room_id, property=prop)
        guest = get_object_or_404(Guest, id=guest_id)

        today = date.today()
        check_out_date = today + timedelta(days=num_nights)

        if Booking.check_overlap(room, today, check_out_date):
            messages.error(request, f"Room {room.room_number} is not available for check-in today.")
            return redirect('dashboard:index')

        with transaction.atomic():
            booking = Booking.objects.create(
                property=prop,
                room=room,
                guest=guest,
                check_in_date=today,
                check_in_time=timezone.now().time(),
                expected_check_out=check_out_date,
                number_of_guests=1,
                nightly_rate=room.price_per_night,
                amount_paid=initial_payment,
                status='checked_in',
                created_by=request.user
            )

            # Update room status to occupied
            room.status = 'occupied'
            room.save()

            # Create Invoice
            invoice = Invoice.objects.create(
                booking=booking,
                subtotal=booking.total_amount,
                tax=0,
                discount=0,
                total=booking.total_amount,
                amount_paid=initial_payment,
                balance=booking.balance,
                status='paid' if booking.balance <= 0 else ('partially_paid' if initial_payment > 0 else 'unpaid')
            )

            InvoiceItem.objects.create(
                invoice=invoice,
                description=f"Room Charge ({room.room_number}) - {num_nights} Night(s)",
                quantity=num_nights,
                unit_price=room.price_per_night,
                total=booking.total_amount
            )

            if initial_payment > 0:
                tx = Transaction.objects.create(
                    property=prop,
                    booking=booking,
                    invoice=invoice,
                    amount=initial_payment,
                    payment_method=payment_method,
                    transaction_status='completed',
                    received_by=request.user
                )

                # Generate initial receipt
                Receipt.objects.create(
                    property=prop,
                    booking=booking,
                    transaction=tx,
                    guest=guest,
                    amount_paid=initial_payment,
                    received_by=request.user
                )

            AuditLog.log_action(
                user=request.user,
                property=prop,
                action='quick_check_in',
                model_name='Booking',
                object_id=str(booking.id),
                new_value=f"Checked-in to Room {room.room_number}"
            )

        messages.success(request, f"Guest {guest.full_name} checked into Room {room.room_number}!")
        return redirect('bookings:detail', booking_id=booking.id)

    return redirect('dashboard:index')


@login_required
def check_in_booking(request, booking_id):
    """Transitions a confirmed/pending reservation to checked_in."""
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.status in ['confirmed', 'pending']:
        with transaction.atomic():
            booking.status = 'checked_in'
            booking.check_in_time = timezone.now().time()
            booking.save()

            room = booking.room
            room.status = 'occupied'
            room.save()

            AuditLog.log_action(
                user=request.user,
                property=booking.property,
                action='check_in_booking',
                model_name='Booking',
                object_id=str(booking.id),
                new_value=f"Checked-in booking {booking.booking_reference} to Room {room.room_number}"
            )

        messages.success(request, f"Booking {booking.booking_reference} is now Checked In. Room #{room.room_number} set to Occupied.")
    else:
        messages.info(request, f"Booking is already in status: {booking.get_status_display()}")

    return redirect('bookings:detail', booking_id=booking.id)


@login_required
def perform_check_out(request, booking_id):
    """Executes Check-Out workflow atomically."""
    booking = get_object_or_404(Booking, id=booking_id)
    invoice = getattr(booking, 'invoice', None)

    if request.method == 'POST':
        extra_charge_amount = Decimal(request.POST.get('extra_charge_amount', '0.00'))
        extra_charge_desc = request.POST.get('extra_charge_desc', 'Additional Service')
        discount_amount = Decimal(request.POST.get('discount_amount', '0.00'))
        tax_amount = Decimal(request.POST.get('tax_amount', '0.00'))
        final_payment = Decimal(request.POST.get('final_payment', '0.00'))
        payment_method = request.POST.get('payment_method', 'cash')

        with transaction.atomic():
            if extra_charge_amount > 0 and invoice:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=extra_charge_desc,
                    quantity=1,
                    unit_price=extra_charge_amount,
                    total=extra_charge_amount
                )
                invoice.subtotal += extra_charge_amount

            if invoice:
                invoice.discount = discount_amount
                invoice.tax = tax_amount
                invoice.total = (invoice.subtotal - discount_amount) + tax_amount
                invoice.amount_paid += final_payment
                invoice.balance = invoice.total - invoice.amount_paid
                invoice.status = 'paid' if invoice.balance <= 0 else 'partially_paid'
                invoice.save()

                booking.total_amount = invoice.total
                booking.amount_paid = invoice.amount_paid
                booking.balance = invoice.balance

            booking.status = 'checked_out'
            booking.actual_check_out = timezone.now()
            booking.save()

            # Room status transitions to cleaning
            room = booking.room
            room.status = 'cleaning'
            room.save()

            # Record final payment transaction & generate final receipt if payment made
            if final_payment > 0:
                tx = Transaction.objects.create(
                    property=booking.property,
                    booking=booking,
                    invoice=invoice,
                    amount=final_payment,
                    payment_method=payment_method,
                    transaction_status='completed',
                    received_by=request.user
                )

                Receipt.objects.create(
                    property=booking.property,
                    booking=booking,
                    transaction=tx,
                    guest=booking.guest,
                    amount_paid=final_payment,
                    received_by=request.user
                )

            # Trigger automated housekeeping cleaning task
            from housekeeping.models import HousekeepingTask
            HousekeepingTask.objects.create(
                property=booking.property,
                room=room,
                task_description=f"Post Checkout Cleaning - Booking {booking.booking_reference}",
                priority='high',
                status='pending'
            )

            AuditLog.log_action(
                user=request.user,
                property=booking.property,
                action='check_out',
                model_name='Booking',
                object_id=str(booking.id),
                new_value=f"Checked out Room {room.room_number}"
            )

        messages.success(request, f"Check-out completed for Booking {booking.booking_reference}. Room {room.room_number} moved to Cleaning.")
        return redirect('bookings:detail', booking_id=booking.id)

    return render(request, 'bookings/checkout_confirm.html', {
        'booking': booking,
        'invoice': invoice
    })
