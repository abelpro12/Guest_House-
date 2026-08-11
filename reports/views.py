import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count, Q

from bookings.models import Booking
from payments.models import Transaction
from rooms.models import Room

from config.permissions import investor_or_admin_required

@login_required
@investor_or_admin_required
def reports_index(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Select property.")
        return redirect('properties:list')

    period = request.GET.get('period', 'daily')
    today = date.today()

    if period == 'weekly':
        start_date = today - timedelta(days=7)
    elif period == 'monthly':
        start_date = today - timedelta(days=30)
    else: # daily
        start_date = today

    transactions = Transaction.objects.filter(
        property=prop,
        transaction_status='completed',
        timestamp__date__gte=start_date
    )

    total_revenue = transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    payment_methods = transactions.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    )

    bookings = Booking.objects.filter(property=prop, check_in_date__gte=start_date)
    total_rooms = Room.objects.filter(property=prop, is_active=True).count()
    occupied_rooms = Room.objects.filter(property=prop, status='occupied').count()
    occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    return render(request, 'reports/index.html', {
        'period': period,
        'start_date': start_date,
        'today': today,
        'total_revenue': total_revenue,
        'payment_methods': payment_methods,
        'total_bookings': bookings.count(),
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'occupancy_rate': occupancy_rate,
        'transactions': transactions[:50]
    })


@login_required
@investor_or_admin_required
def export_csv(request):
    prop = getattr(request, 'current_property', None)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Financial_Report_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Reference', 'Booking Ref', 'Date/Time', 'Payment Method', 'Amount (ETB)', 'Received By', 'Status'])

    transactions = Transaction.objects.filter(property=prop).order_by('-timestamp') if prop else []
    for tx in transactions:
        writer.writerow([
            tx.reference_id,
            tx.booking.booking_reference if tx.booking else '',
            tx.timestamp.strftime('%Y-%m-%d %H:%M'),
            tx.get_payment_method_display(),
            tx.amount,
            tx.received_by.get_full_name() if tx.received_by else '',
            tx.get_transaction_status_display()
        ])

    return response


@login_required
@investor_or_admin_required
def export_excel(request):
    prop = getattr(request, 'current_property', None)
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Financial Transactions"

        headers = ['Reference ID', 'Booking Ref', 'Date/Time', 'Payment Method', 'Amount (ETB)', 'Received By', 'Status']
        ws.append(headers)

        transactions = Transaction.objects.filter(property=prop).order_by('-timestamp') if prop else []
        for tx in transactions:
            ws.append([
                tx.reference_id,
                tx.booking.booking_reference if tx.booking else '',
                tx.timestamp.strftime('%Y-%m-%d %H:%M'),
                tx.get_payment_method_display(),
                float(tx.amount),
                tx.received_by.get_full_name() if tx.received_by else '',
                tx.get_transaction_status_display()
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Financial_Report_{date.today()}.xlsx"'
        wb.save(response)
        return response
    except Exception as e:
        messages.error(request, f"Excel export error: {str(e)}")
        return redirect('reports:index')


@login_required
@investor_or_admin_required
def night_audit(request):
    """Generates an end-of-day Night Audit report reconciling occupancy, collections, and pending balances."""
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Select property.")
        return redirect('properties:list')

    today = date.today()
    rooms = Room.objects.filter(property=prop, is_active=True)
    total_rooms = rooms.count()
    occupied_rooms = rooms.filter(status='occupied').count()
    maintenance_rooms = rooms.filter(status='maintenance').count()
    vacant_rooms = rooms.filter(status='vacant').count()
    cleaning_rooms = rooms.filter(status='cleaning').count()

    occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    # Today's Check-ins & Check-outs
    check_ins = Booking.objects.filter(property=prop, check_in_date=today)
    check_outs = Booking.objects.filter(property=prop, expected_check_out=today)

    # Today's Collections Breakdown
    today_txs = Transaction.objects.filter(property=prop, transaction_status='completed', timestamp__date=today)
    total_collected = today_txs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    pm_breakdown = today_txs.values('payment_method').annotate(total=Sum('amount'), count=Count('id'))

    # Active Outstanding Balances
    active_bookings = Booking.objects.filter(property=prop, status__in=['confirmed', 'checked_in'])
    total_outstanding = active_bookings.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

    return render(request, 'reports/night_audit.html', {
        'property': prop,
        'today': today,
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'vacant_rooms': vacant_rooms,
        'cleaning_rooms': cleaning_rooms,
        'maintenance_rooms': maintenance_rooms,
        'occupancy_rate': occupancy_rate,
        'check_ins': check_ins,
        'check_outs': check_outs,
        'total_collected': total_collected,
        'pm_breakdown': pm_breakdown,
        'total_outstanding': total_outstanding,
        'today_txs': today_txs
    })
