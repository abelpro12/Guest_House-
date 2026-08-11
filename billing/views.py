from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Invoice, InvoiceItem, ExtraService

@login_required
def invoice_list(request):
    prop = getattr(request, 'current_property', None)
    invoices = Invoice.objects.filter(booking__property=prop).order_by('-created_at') if prop else Invoice.objects.none()
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})

@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    prop = getattr(request, 'current_property', None)
    if prop and not ExtraService.objects.filter(property=prop).exists():
        # Seed default amenities & POS catalog for property
        ExtraService.objects.bulk_create([
            ExtraService(property=prop, name='Breakfast Buffet', category='food_beverage', unit_price=Decimal('250.00')),
            ExtraService(property=prop, name='Full Service Laundry (per bag)', category='laundry', unit_price=Decimal('150.00')),
            ExtraService(property=prop, name='Airport Pick-up / Drop-off Shuttle', category='transport', unit_price=Decimal('600.00')),
            ExtraService(property=prop, name='Rollaway Extra Bed', category='facility', unit_price=Decimal('400.00')),
            ExtraService(property=prop, name='Mineral Water (1.5L)', category='food_beverage', unit_price=Decimal('35.00')),
        ])
    services = ExtraService.objects.filter(property=prop, is_active=True) if prop else ExtraService.objects.none()
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice, 'services': services})

@login_required
def add_invoice_item(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        description = request.POST.get('description')
        quantity = int(request.POST.get('quantity', 1))
        unit_price_str = request.POST.get('unit_price')

        if service_id:
            service = get_object_or_404(ExtraService, id=service_id)
            description = service.name
            unit_price = service.unit_price
        else:
            unit_price = Decimal(unit_price_str or '0.00')

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
