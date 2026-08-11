from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import date
from .models import Expense, StaffPayroll, StaffAttendance
from properties.models import Property, PropertyStaff
from billing.models import Invoice
from accounts.models import CustomUser
from config.permissions import investor_or_admin_required, staff_required

def get_current_property(request):
    prop_id = request.GET.get('property_id') or request.session.get('current_property_id')
    if prop_id:
        p = Property.objects.filter(id=prop_id).first()
        if p:
            request.session['current_property_id'] = p.id
            return p
    if hasattr(request, 'current_property') and request.current_property:
        return request.current_property
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

    # Selected Month Handling
    from datetime import datetime
    month_param = request.GET.get('month')
    if month_param:
        try:
            selected_date = datetime.strptime(month_param, '%Y-%m').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    selected_year = selected_date.year
    selected_month = selected_date.month
    selected_month_str = selected_date.strftime('%Y-%m')
    month_name = selected_date.strftime('%B %Y')

    # Filter transactions for selected month
    expenses = Expense.objects.filter(property=prop, expense_date__year=selected_year, expense_date__month=selected_month).order_by('-expense_date')
    payrolls = StaffPayroll.objects.filter(property=prop, created_at__year=selected_year, created_at__month=selected_month).order_by('-created_at')
    invoices = Invoice.objects.filter(booking__property=prop, status='paid', created_at__year=selected_year, created_at__month=selected_month)
    attendances = StaffAttendance.objects.filter(property=prop, date=date.today())

    # Revenue & Expenses calculations for selected month
    total_revenue = invoices.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    net_profit = total_revenue - total_expenses

    # Category breakdown for selected month
    expenses_by_cat = expenses.values('category').annotate(cat_total=Sum('amount'))
    cat_names = dict(Expense.CATEGORY_CHOICES)
    cat_summary = [
        {'category': cat_names.get(item['category'], item['category']), 'total': item['cat_total']}
        for item in expenses_by_cat
    ]

    # Tax estimations for selected month
    estimated_vat = total_revenue * Decimal('0.15') # 15% VAT
    payroll_taxes = payrolls.aggregate(Sum('tax_deduction'))['tax_deduction__sum'] or Decimal('0.00')
    total_tax_liability = estimated_vat + payroll_taxes

    # Salary commitments & paid payrolls for selected month
    staff_commitments = PropertyStaff.objects.filter(property=prop, is_active=True)
    total_salary_commitment = staff_commitments.aggregate(Sum('base_salary'))['base_salary__sum'] or Decimal('0.00')
    total_payroll_paid = payrolls.filter(status='paid').aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')

    # Build 6-Month Comparison Matrix
    from datetime import timedelta
    monthly_comparison = []
    curr = date.today().replace(day=1)
    for _ in range(6):
        m_year = curr.year
        m_month = curr.month
        m_label = curr.strftime('%b %Y')
        
        m_rev = Invoice.objects.filter(booking__property=prop, status='paid', created_at__year=m_year, created_at__month=m_month).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        m_exp = Expense.objects.filter(property=prop, expense_date__year=m_year, expense_date__month=m_month).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        m_profit = m_rev - m_exp
        
        monthly_comparison.append({
            'month_key': curr.strftime('%Y-%m'),
            'month_label': m_label,
            'revenue': m_rev,
            'expenses': m_exp,
            'profit': m_profit,
            'is_selected': (m_year == selected_year and m_month == selected_month)
        })
        prev_month_end = curr - timedelta(days=1)
        curr = prev_month_end.replace(day=1)

    if total_revenue > 0:
        profit_margin = round((net_profit / total_revenue) * Decimal('100.0'), 1)
    else:
        profit_margin = Decimal('0.0')

    return render(request, 'finance/dashboard.html', {
        'property': prop,
        'month_name': month_name,
        'selected_month_str': selected_month_str,
        'monthly_comparison': monthly_comparison,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'profit_margin': profit_margin,
        'cat_summary': cat_summary,
        'estimated_vat': estimated_vat,
        'payroll_taxes': payroll_taxes,
        'total_tax_liability': total_tax_liability,
        'total_salary_commitment': total_salary_commitment,
        'total_payroll_paid': total_payroll_paid,
        'all_month_expenses': expenses,
        'all_month_invoices': invoices,
        'recent_expenses': expenses[:5],
        'recent_payrolls': payrolls[:5],
        'today_attendances': attendances,
    })


@login_required
@investor_or_admin_required
def expense_list(request):
    prop = get_current_property(request)
    category_filter = request.GET.get('category', '')
    expenses_qs = Expense.objects.filter(property=prop).order_by('-expense_date')

    if category_filter:
        expenses_qs = expenses_qs.filter(category=category_filter)

    paginator = Paginator(expenses_qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    categories = Expense.CATEGORY_CHOICES
    payment_methods = Expense.PAYMENT_METHOD_CHOICES

    return render(request, 'finance/expense_list.html', {
        'property': prop,
        'expenses': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'payment_methods': payment_methods,
        'category_filter': category_filter,
    })


@login_required
@investor_or_admin_required
def expense_create(request):
    if request.method == 'POST':
        prop = get_current_property(request)
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        expense_date = request.POST.get('expense_date') or date.today()
        paid_to = request.POST.get('paid_to', '').strip()
        payment_method = request.POST.get('payment_method', 'cash')
        receipt_ref = request.POST.get('receipt_reference', '').strip()
        notes = request.POST.get('notes', '').strip()

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
@investor_or_admin_required
def payroll_list(request):
    prop = get_current_property(request)
    payrolls_qs = StaffPayroll.objects.filter(property=prop).order_by('-created_at')
    
    paginator = Paginator(payrolls_qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    staff_assignments = PropertyStaff.objects.filter(property=prop).select_related('user')

    return render(request, 'finance/payroll_list.html', {
        'property': prop,
        'payrolls': page_obj,
        'page_obj': page_obj,
        'staff_assignments': staff_assignments,
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
    if not (request.user.is_receptionist or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted to receptionists and admins.")
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

    # Calculate monthly summary statistics & generate exact calendar matrix per staff
    import calendar
    year = selected_date.year
    month = selected_date.month
    _, num_days = calendar.monthrange(year, month)
    days_in_month = [date(year, month, d) for d in range(1, num_days + 1)]

    month_attendances = StaffAttendance.objects.filter(
        property=prop,
        date__year=year,
        date__month=month
    )
    month_att_map = {(att.staff_member_id, att.date.day): att for att in month_attendances}

    staff_summaries = []
    calendar_rows = []

    for staff in staff_users:
        user_recs = month_attendances.filter(staff_member=staff)
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

        # Build day cells for calendar view
        day_cells = []
        for d in range(1, num_days + 1):
            att = month_att_map.get((staff.id, d))
            day_cells.append({
                'day': d,
                'date_str': date(year, month, d).isoformat(),
                'attendance': att,
            })

        calendar_rows.append({
            'staff': staff,
            'day_cells': day_cells,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'leave_count': leave_count,
            'total_overtime': total_overtime,
        })

    return render(request, 'finance/attendance_list.html', {
        'property': prop,
        'staff_summaries': staff_summaries,
        'calendar_rows': calendar_rows,
        'days_in_month': days_in_month,
        'num_days': range(1, num_days + 1),
        'selected_date': selected_date,
        'month_name': selected_date.strftime('%B %Y'),
        'statuses': StaffAttendance.STATUS_CHOICES,
    })


@login_required
def attendance_log(request):
    if not (request.user.is_receptionist or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted to receptionists and admins.")
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
        return redirect(f"/attendance/?date={att_date}")

    return redirect('attendance_direct')


@login_required
def attendance_bulk_mark(request):
    """1-Click action to mark all assigned staff present for today."""
    if not (request.user.is_receptionist or request.user.is_investor or request.user.is_admin):
        messages.error(request, "Access restricted to receptionists and admins.")
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
    return redirect(f"/attendance/?date={att_date}")
