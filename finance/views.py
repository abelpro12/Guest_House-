from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import date
from .models import Expense, StaffPayroll, StaffAttendance
from properties.models import Property, PropertyStaff
from billing.models import Invoice
from accounts.models import CustomUser

def get_current_property(request):
    prop_id = request.session.get('current_property_id')
    if prop_id:
        return Property.objects.filter(id=prop_id).first()
    return Property.objects.first()

@login_required
def finance_dashboard(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted to Finance, Owner, and Admin profiles.")
        return redirect('dashboard:index')

    prop = get_current_property(request)
    if not prop:
        messages.warning(request, "No property found.")
        return redirect('dashboard:index')

    expenses = Expense.objects.filter(property=prop).order_by('-expense_date')
    payrolls = StaffPayroll.objects.filter(property=prop).order_by('-created_at')
    attendances = StaffAttendance.objects.filter(property=prop, date=date.today())

    # Revenue calculation from paid invoices
    invoices = Invoice.objects.filter(booking__property=prop, status='paid')
    total_revenue = invoices.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')

    # Expense calculation
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    net_profit = total_revenue - total_expenses

    # Category breakdown
    expenses_by_cat = expenses.values('category').annotate(cat_total=Sum('amount'))
    cat_names = dict(Expense.CATEGORY_CHOICES)
    cat_summary = [
        {'category': cat_names.get(item['category'], item['category']), 'total': item['cat_total']}
        for item in expenses_by_cat
    ]

    # Tax estimations
    estimated_vat = total_revenue * Decimal('0.15') # 15% VAT
    payroll_taxes = payrolls.aggregate(Sum('tax_deduction'))['tax_deduction__sum'] or Decimal('0.00')
    total_tax_liability = estimated_vat + payroll_taxes

    return render(request, 'finance/dashboard.html', {
        'property': prop,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'cat_summary': cat_summary,
        'estimated_vat': estimated_vat,
        'payroll_taxes': payroll_taxes,
        'total_tax_liability': total_tax_liability,
        'recent_expenses': expenses[:5],
        'recent_payrolls': payrolls[:5],
        'today_attendances': attendances,
    })


@login_required
def expense_list(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    prop = get_current_property(request)
    category_filter = request.GET.get('category', '')
    expenses = Expense.objects.filter(property=prop).order_by('-expense_date')

    if category_filter:
        expenses = expenses.filter(category=category_filter)

    categories = Expense.CATEGORY_CHOICES
    payment_methods = Expense.PAYMENT_METHOD_CHOICES

    return render(request, 'finance/expense_list.html', {
        'property': prop,
        'expenses': expenses,
        'categories': categories,
        'payment_methods': payment_methods,
        'category_filter': category_filter,
    })


@login_required
def expense_create(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        prop = get_current_property(request)
        title = request.POST.get('title')
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        expense_date = request.POST.get('expense_date') or date.today()
        paid_to = request.POST.get('paid_to')
        payment_method = request.POST.get('payment_method', 'cash')
        receipt_ref = request.POST.get('receipt_reference')
        notes = request.POST.get('notes')

        Expense.objects.create(
            property=prop,
            title=title,
            category=category,
            amount=Decimal(amount),
            expense_date=expense_date,
            paid_to=paid_to,
            payment_method=payment_method,
            receipt_reference=receipt_ref,
            notes=notes,
            created_by=request.user
        )
        messages.success(request, f"Expense '{title}' recorded successfully!")
        return redirect('finance:expense_list')

    return redirect('finance:expense_list')


@login_required
def payroll_list(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    prop = get_current_property(request)
    payrolls = StaffPayroll.objects.filter(property=prop).order_by('-created_at')
    
    # Get staff list for modal
    staff_assignments = PropertyStaff.objects.filter(property=prop).select_related('user')
    staff_users = [ps.user for ps in staff_assignments]

    return render(request, 'finance/payroll_list.html', {
        'property': prop,
        'payrolls': payrolls,
        'staff_users': staff_users,
    })


@login_required
def payroll_create(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        prop = get_current_property(request)
        staff_id = request.POST.get('staff_id')
        period_name = request.POST.get('period_name')
        base_salary = Decimal(request.POST.get('base_salary', '0.00'))
        bonus = Decimal(request.POST.get('bonus', '0.00'))
        deductions = Decimal(request.POST.get('deductions', '0.00'))
        tax_deduction = Decimal(request.POST.get('tax_deduction', '0.00'))
        status = request.POST.get('status', 'draft')
        paid_on = request.POST.get('paid_on') or None
        notes = request.POST.get('notes')

        staff_user = get_object_or_404(CustomUser, id=staff_id)

        payroll = StaffPayroll.objects.create(
            property=prop,
            staff_member=staff_user,
            period_name=period_name,
            base_salary=base_salary,
            bonus=bonus,
            deductions=deductions,
            tax_deduction=tax_deduction,
            status=status,
            paid_on=paid_on if status == 'paid' else None,
            notes=notes
        )

        # Automatically log expense if paid
        if status == 'paid':
            Expense.objects.create(
                property=prop,
                category='payroll',
                title=f"Salary Payout: {staff_user.get_full_name() or staff_user.username} ({period_name})",
                amount=payroll.net_salary,
                expense_date=paid_on or date.today(),
                paid_to=staff_user.get_full_name() or staff_user.username,
                payment_method='bank_transfer',
                receipt_reference=f"PAYROLL-{payroll.id}",
                created_by=request.user
            )

        messages.success(request, f"Payroll record created for {staff_user.username}!")
        return redirect('finance:payroll_list')

    return redirect('finance:payroll_list')


@login_required
def attendance_list(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin or request.user.is_receptionist):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    prop = get_current_property(request)
    selected_date_str = request.GET.get('date', date.today().isoformat())
    
    try:
        selected_date = date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = date.today()

    attendances = StaffAttendance.objects.filter(property=prop, date=selected_date)
    att_dict = {att.staff_member_id: att for att in attendances}

    staff_assignments = PropertyStaff.objects.filter(property=prop).select_related('user')
    staff_users = [ps.user for ps in staff_assignments]

    # Calculate monthly summary statistics per staff
    first_of_month = selected_date.replace(day=1)
    monthly_records = StaffAttendance.objects.filter(property=prop, date__gte=first_of_month, date__lte=selected_date)

    staff_summaries = []
    for staff in staff_users:
        user_recs = monthly_records.filter(staff_member=staff)
        present_count = user_recs.filter(status='present').count()
        absent_count = user_recs.filter(status='absent').count()
        late_count = user_recs.filter(status='late').count()
        leave_count = user_recs.filter(status='leave').count()
        total_overtime = user_recs.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or Decimal('0.00')

        staff_summaries.append({
            'staff': staff,
            'attendance': att_dict.get(staff.id),
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'leave_count': leave_count,
            'total_overtime': total_overtime,
        })

    return render(request, 'finance/attendance_list.html', {
        'property': prop,
        'staff_summaries': staff_summaries,
        'selected_date': selected_date,
        'statuses': StaffAttendance.STATUS_CHOICES,
    })


@login_required
def attendance_log(request):
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin or request.user.is_receptionist):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        prop = get_current_property(request)
        staff_id = request.POST.get('staff_id')
        att_date = request.POST.get('date', date.today().isoformat())
        status = request.POST.get('status', 'present')
        check_in = request.POST.get('check_in_time') or None
        check_out = request.POST.get('check_out_time') or None
        hours_worked = Decimal(request.POST.get('hours_worked', '8.00'))
        overtime_hours = Decimal(request.POST.get('overtime_hours', '0.00'))
        notes = request.POST.get('notes')

        staff_user = get_object_or_404(CustomUser, id=staff_id)

        StaffAttendance.objects.update_or_create(
            property=prop,
            staff_member=staff_user,
            date=att_date,
            defaults={
                'status': status,
                'check_in_time': check_in,
                'check_out_time': check_out,
                'hours_worked': hours_worked,
                'overtime_hours': overtime_hours,
                'notes': notes
            }
        )
        messages.success(request, f"Attendance & hours logged for {staff_user.username} on {att_date}!")
        return redirect(f"/finance/attendance/?date={att_date}")

    return redirect('finance:attendance_list')


@login_required
def attendance_bulk_mark(request):
    """1-Click action to mark all assigned staff present for today."""
    if not (request.user.is_accountant or request.user.is_investor or request.user.is_admin or request.user.is_receptionist):
        messages.error(request, "Access restricted.")
        return redirect('dashboard:index')

    prop = get_current_property(request)
    att_date = request.GET.get('date', date.today().isoformat())

    staff_assignments = PropertyStaff.objects.filter(property=prop).select_related('user')
    count = 0
    for ps in staff_assignments:
        StaffAttendance.objects.update_or_create(
            property=prop,
            staff_member=ps.user,
            date=att_date,
            defaults={'status': 'present', 'hours_worked': Decimal('8.00')}
        )
        count += 1

    messages.success(request, f"Successfully marked all {count} staff members Present for {att_date}!")
    return redirect(f"/finance/attendance/?date={att_date}")
