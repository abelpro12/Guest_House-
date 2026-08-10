from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Invoice, InvoiceItem

@login_required
def invoice_list(request):
    prop = getattr(request, 'current_property', None)
    invoices = Invoice.objects.filter(booking__property=prop).order_by('-created_at') if prop else Invoice.objects.none()
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})

@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})

@login_required
def add_invoice_item(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        description = request.POST.get('description')
        quantity = int(request.POST.get('quantity', 1))
        unit_price = Decimal(request.POST.get('unit_price', '0.00'))

        item = InvoiceItem.objects.create(
            invoice=invoice,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            total=quantity * unit_price
        )

        # Recalculate subtotal & total
        invoice.subtotal += item.total
        invoice.total = (invoice.subtotal - invoice.discount) + invoice.tax
        invoice.save()

        # Update booking total amount
        booking = invoice.booking
        booking.total_amount = invoice.total
        booking.save()

        messages.success(request, f"Added '{description}' to invoice.")
    return redirect('billing:detail', invoice_id=invoice.id)
