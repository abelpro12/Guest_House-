from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Shift
from audit.models import AuditLog

@login_required
def shift_list(request):
    prop = getattr(request, 'current_property', None)
    shifts = Shift.objects.filter(property=prop).order_by('-start_time') if prop else Shift.objects.none()
    current_shift = Shift.objects.filter(property=prop, receptionist=request.user, status='open').first() if prop else None
    
    return render(request, 'shifts/shift_list.html', {
        'shifts': shifts,
        'current_shift': current_shift
    })

@login_required
def start_shift(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Please select a property first.")
        return redirect('properties:list')

    # Check if there is an active open shift for user
    open_shift = Shift.objects.filter(property=prop, receptionist=request.user, status='open').first()
    if open_shift:
        messages.info(request, "You already have an active open shift.")
        return redirect('shifts:list')

    if request.method == 'POST':
        opening_cash = Decimal(request.POST.get('opening_cash', '0.00'))
        shift = Shift.objects.create(
            property=prop,
            receptionist=request.user,
            opening_cash=opening_cash,
            status='open'
        )
        AuditLog.log_action(
            user=request.user,
            property=prop,
            action='start_shift',
            model_name='Shift',
            object_id=str(shift.id),
            new_value=f"Opened shift with {opening_cash} ETB"
        )
        messages.success(request, f"Shift started with opening cash of {opening_cash} ETB.")
        return redirect('shifts:list')

    return render(request, 'shifts/start_shift.html')

@login_required
def close_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    if request.method == 'POST':
        actual_cash = Decimal(request.POST.get('actual_cash', '0.00'))
        shift.close_shift(actual_cash)

        AuditLog.log_action(
            user=request.user,
            property=shift.property,
            action='close_shift',
            model_name='Shift',
            object_id=str(shift.id),
            new_value=f"Closed shift. Actual: {actual_cash}, Expected: {shift.expected_cash}, Diff: {shift.difference}"
        )

        messages.success(request, f"Shift closed. Cash difference: {shift.difference} ETB.")
        return redirect('shifts:list')

    expected_cash = shift.calculate_expected_cash()
    return render(request, 'shifts/close_shift.html', {
        'shift': shift,
        'expected_cash': expected_cash
    })
