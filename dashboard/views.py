from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q

from accounts.models import CustomUser
from properties.models import Property
from rooms.models import Room, RoomType
from bookings.models import Booking
from payments.models import Transaction
from shifts.models import Shift
from housekeeping.models import HousekeepingTask
from maintenance.models import MaintenanceTicket
from subscriptions.models import PropertySubscription
from audit.models import AuditLog
from guests.models import Guest

@login_required
def index_view(request):
    user = request.user
    if user.is_admin:
        return admin_dashboard(request)
    elif user.is_investor:
        return investor_dashboard(request)
    elif user.is_accountant:
        return redirect('finance:dashboard')
    elif user.is_receptionist:
        return receptionist_dashboard(request)
    elif user.is_guest:
        return guest_portal(request)
    return receptionist_dashboard(request)


@login_required
def receptionist_dashboard(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        return render(request, 'dashboard/no_property.html')

    today = date.today()
    rooms = Room.objects.filter(property=prop, is_active=True).select_related('room_type')
    
    # Counts
    total_rooms = rooms.count()
    vacant_count = rooms.filter(status='vacant').count()
    occupied_count = rooms.filter(status='occupied').count()
    cleaning_count = rooms.filter(status='cleaning').count()
    maintenance_count = rooms.filter(status='maintenance').count()
    unavailable_count = rooms.filter(status='unavailable').count()

    today_arrivals = Booking.objects.filter(property=prop, check_in_date=today, status__in=['confirmed', 'checked_in'])
    today_departures = Booking.objects.filter(property=prop, expected_check_out=today, status__in=['checked_in', 'checked_out'])

    today_revenue = Transaction.objects.filter(
        property=prop,
        transaction_status='completed',
        timestamp__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Shift status
    active_shift = Shift.objects.filter(property=prop, receptionist=request.user, status='open').first()

    guests = Guest.objects.all().order_by('-created_at')[:20]

    return render(request, 'dashboard/receptionist_dashboard.html', {
        'property': prop,
        'rooms': rooms,
        'total_rooms': total_rooms,
        'vacant_count': vacant_count,
        'occupied_count': occupied_count,
        'cleaning_count': cleaning_count,
        'maintenance_count': maintenance_count,
        'unavailable_count': unavailable_count,
        'today_arrivals': today_arrivals,
        'today_departures': today_departures,
        'today_revenue': today_revenue,
        'active_shift': active_shift,
        'guests': guests
    })


@login_required
def investor_dashboard(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        return render(request, 'dashboard/no_property.html')

    today = date.today()

    # Revenue calculation
    daily_revenue = Transaction.objects.filter(property=prop, transaction_status='completed', timestamp__date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    weekly_revenue = Transaction.objects.filter(property=prop, transaction_status='completed', timestamp__date__gte=today - timedelta(days=7)).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    monthly_revenue = Transaction.objects.filter(property=prop, transaction_status='completed', timestamp__date__gte=today - timedelta(days=30)).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    total_rooms = Room.objects.filter(property=prop, is_active=True).count()
    occupied_rooms = Room.objects.filter(property=prop, status='occupied').count()
    occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    payment_breakdown = Transaction.objects.filter(property=prop, transaction_status='completed').values('payment_method').annotate(total=Sum('amount'))

    # 7-day revenue trend calculation for Chart.js
    revenue_chart_labels = []
    revenue_chart_data = []
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_str = day_date.strftime('%b %d')
        day_rev = Transaction.objects.filter(
            property=prop,
            transaction_status='completed',
            timestamp__date=day_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        revenue_chart_labels.append(day_str)
        revenue_chart_data.append(float(day_rev))

    recent_shifts = Shift.objects.filter(property=prop).order_by('-start_time')[:10]
    audit_logs = AuditLog.objects.filter(property=prop).order_by('-timestamp')[:20]
    subscription = getattr(prop, 'subscription', None)

    return render(request, 'dashboard/investor_dashboard.html', {
        'property': prop,
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'occupancy_rate': occupancy_rate,
        'payment_breakdown': payment_breakdown,
        'revenue_chart_labels': revenue_chart_labels,
        'revenue_chart_data': revenue_chart_data,
        'recent_shifts': recent_shifts,
        'audit_logs': audit_logs,
        'subscription': subscription
    })


@login_required
def admin_dashboard(request):
    if not request.user.is_admin:
        return redirect('dashboard:index')

    total_investors = CustomUser.objects.filter(role='investor').count()
    total_properties = Property.objects.count()
    total_rooms = Room.objects.count()

    active_subs = PropertySubscription.objects.filter(is_active=True).count()
    expired_subs = PropertySubscription.objects.filter(is_active=False).count()

    investors = CustomUser.objects.filter(role='investor')
    properties = Property.objects.select_related('investor', 'subscription').all()
    audit_logs = AuditLog.objects.all().order_by('-timestamp')[:25]

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_investors': total_investors,
        'total_properties': total_properties,
        'total_rooms': total_rooms,
        'active_subs': active_subs,
        'expired_subs': expired_subs,
        'investors': investors,
        'properties': properties,
        'audit_logs': audit_logs
    })


@login_required
def guest_portal(request):
    guest = getattr(request.user, 'guest_profile', None)
    if not guest:
        # Create profile if missing
        guest = Guest.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
            phone_number=request.user.phone_number or '',
            email=request.user.email or ''
        )

    bookings = Booking.objects.filter(guest=guest).select_related('room', 'property').order_by('-created_at')
    active_booking = bookings.filter(status='checked_in').first()

    return render(request, 'dashboard/guest_portal.html', {
        'guest': guest,
        'bookings': bookings,
        'active_booking': active_booking
    })
