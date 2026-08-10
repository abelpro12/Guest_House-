from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Transaction
from bookings.models import Booking
from billing.models import Invoice
from receipts.models import Receipt
from audit.models import AuditLog

@login_required
def transaction_list(request):
    prop = getattr(request, 'current_property', None)
    transactions = Transaction.objects.filter(property=prop).order_by('-timestamp') if prop else Transaction.objects.none()
    return render(request, 'payments/transaction_list.html', {'transactions': transactions})

@login_required
def record_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0.00'))
        method = request.POST.get('payment_method', 'cash')
        ref_note = request.POST.get('reference_id', '')

        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('bookings:detail', booking_id=booking.id)

        with transaction.atomic():
            invoice = getattr(booking, 'invoice', None)
            
            tx = Transaction.objects.create(
                property=booking.property,
                booking=booking,
                invoice=invoice,
                amount=amount,
                payment_method=method,
                reference_id=ref_note or None,
                transaction_status='completed',
                received_by=request.user
            )

            booking.amount_paid += amount
            booking.save()

            if invoice:
                invoice.amount_paid += amount
                invoice.save()

            # Create Receipt
            Receipt.objects.create(
                property=booking.property,
                booking=booking,
                transaction=tx,
                guest=booking.guest,
                amount_paid=amount,
                received_by=request.user
            )

            AuditLog.log_action(
                user=request.user,
                property=booking.property,
                action='record_payment',
                model_name='Transaction',
                object_id=str(tx.id),
                new_value=f"Paid {amount} ETB via {method}"
            )

        messages.success(request, f"Payment of {amount} ETB recorded successfully!")
    return redirect('bookings:detail', booking_id=booking.id)

@login_required
def void_transaction(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id)
    if not (request.user.is_admin or request.user.is_investor):
        messages.error(request, "Permission denied. Only Admin or Investor can void transactions.")
        return redirect('payments:list')

    if request.method == 'POST':
        reason = request.POST.get('reason', 'User requested void')
        with transaction.atomic():
            tx.transaction_status = 'voided'
            tx.save()

            # Revert amounts
            booking = tx.booking
            booking.amount_paid = max(Decimal('0.00'), booking.amount_paid - tx.amount)
            booking.save()

            if tx.invoice:
                invoice = tx.invoice
                invoice.amount_paid = max(Decimal('0.00'), invoice.amount_paid - tx.amount)
                invoice.save()

            AuditLog.log_action(
                user=request.user,
                property=tx.property,
                action='void_transaction',
                model_name='Transaction',
                object_id=str(tx.id),
                old_value=f"{tx.amount} ETB",
                new_value=f"VOIDED - Reason: {reason}"
            )

        messages.success(request, f"Transaction #{tx.reference_id} was successfully voided.")
    return redirect('payments:list')
