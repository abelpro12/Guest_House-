import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Receipt
from audit.models import AuditLog

@login_required
def receipt_detail(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    # Enforce property permission or guest ownership
    if request.user.is_guest and receipt.guest.user != request.user:
        messages.error(request, "Permission denied.")
        return redirect('dashboard:index')
    return render(request, 'receipts/receipt_detail.html', {'receipt': receipt})

@login_required
def receipt_pdf(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if request.user.is_guest and receipt.guest.user != request.user:
        return HttpResponse("Unauthorized", status=403)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4
        )

        sub_style = ParagraphStyle(
            'SubStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#475569'),
            spaceAfter=12
        )

        elements.append(Paragraph(f"<b>{receipt.property.property_name}</b>", title_style))
        prop_info = f"{receipt.property.address} | Phone: {receipt.property.phone} | Email: {receipt.property.email}"
        if receipt.property.tin_number:
            prop_info += f" | TIN: {receipt.property.tin_number}"
        elements.append(Paragraph(prop_info, sub_style))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(f"<b>OFFICIAL PAYMENT RECEIPT</b> #{receipt.receipt_number}", styles['Heading2']))
        if receipt.is_voided:
            elements.append(Paragraph("<font color='red'><b>*** THIS RECEIPT IS VOIDED ***</b></font>", styles['Heading3']))
        elements.append(Spacer(1, 10))

        data = [
            ["Receipt Date:", receipt.created_at.strftime('%Y-%m-%d %H:%M')],
            ["Guest Name:", receipt.guest.full_name],
            ["ID Document:", f"{receipt.guest.get_id_document_type_display()} - {receipt.guest.id_document_number}"],
            ["Room Number:", f"Room {receipt.booking.room.room_number}"],
            ["Booking Ref:", receipt.booking.booking_reference],
            ["Check-In Date:", str(receipt.booking.check_in_date)],
            ["Check-Out Date:", str(receipt.booking.expected_check_out)],
            ["Payment Method:", receipt.transaction.get_payment_method_display() if receipt.transaction else "Cash"],
            ["Total Amount Paid:", f"<b>{receipt.amount_paid} ETB</b>"],
            ["Received By:", receipt.received_by.get_full_name() if receipt.received_by else "Staff"],
        ]

        if receipt.property.vat_rate > 0 or receipt.property.tot_rate > 0:
            subtotal_val = round(receipt.amount_paid / Decimal(1 + (receipt.property.vat_rate + receipt.property.tot_rate) / 100), 2)
            vat_val = round(subtotal_val * (receipt.property.vat_rate / 100), 2)
            data.insert(8, ["Subtotal (Excl. Tax):", f"{subtotal_val} ETB"])
            if receipt.property.vat_rate > 0:
                data.insert(9, [f"VAT ({receipt.property.vat_rate}%):", f"{vat_val} ETB"])

        t = Table(data, colWidths=[160, 360])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0f172a')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))

        elements.append(t)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Thank you for choosing our guest house!", styles['Italic']))

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Receipt_{receipt.receipt_number}.pdf"'
        return response

    except Exception as e:
        messages.error(request, f"Could not generate PDF: {str(e)}")
        return redirect('receipts:detail', receipt_id=receipt.id)


@login_required
def void_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if not (request.user.is_admin or request.user.is_investor):
        messages.error(request, "Permission denied. Only Admin or Investor can void receipts.")
        return redirect('receipts:detail', receipt_id=receipt.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Admin Void')
        receipt.is_voided = True
        receipt.void_reason = reason
        receipt.save()

        AuditLog.log_action(
            user=request.user,
            property=receipt.property,
            action='void_receipt',
            model_name='Receipt',
            object_id=str(receipt.id),
            new_value=f"Voided Receipt #{receipt.receipt_number} - Reason: {reason}"
        )

        messages.warning(request, f"Receipt #{receipt.receipt_number} has been voided.")
    return redirect('receipts:detail', receipt_id=receipt.id)
