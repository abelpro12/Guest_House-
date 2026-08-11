from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Property, PropertyStaff
from accounts.models import CustomUser

@login_required
def select_property(request, property_id):
    prop = get_object_or_404(Property, id=property_id)
    # Check permissions
    if request.user.is_admin or prop.investor == request.user or PropertyStaff.objects.filter(property=prop, user=request.user, is_active=True).exists():
        request.session['selected_property_id'] = prop.id
        request.session.modified = True
        messages.success(request, f"Switched active property to {prop.property_name}")
    else:
        messages.error(request, "Permission denied for this property.")
    return redirect('dashboard:index')

@login_required
def list_properties(request):
    if request.user.is_admin:
        props = Property.objects.all()
    elif request.user.is_investor:
        props = Property.objects.filter(investor=request.user)
    else:
        props = Property.objects.filter(staff_members__user=request.user)
    return render(request, 'properties/property_list.html', {'properties': props})

@login_required
def create_property(request):
    if not (request.user.is_admin or request.user.is_investor):
        messages.error(request, "Permission denied.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        name = request.POST.get('property_name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        investor_id = request.POST.get('investor_id')

        investor = request.user
        if request.user.is_admin and investor_id:
            investor = CustomUser.objects.filter(id=investor_id, role='investor').first() or request.user

        prop = Property.objects.create(
            property_name=name,
            address=address,
            phone=phone,
            email=email,
            investor=investor
        )

        # Trigger automatic 365-day free trial subscription creation
        from subscriptions.models import PropertySubscription
        from datetime import date, timedelta
        PropertySubscription.objects.create(
            property=prop,
            investor=investor,
            is_trial=True,
            is_active=True,
            start_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            billing_period='annual'
        )

        messages.success(request, f"Property '{prop.property_name}' created with 365-day free trial!")
        return redirect('properties:list')

    investors = CustomUser.objects.filter(role='investor') if request.user.is_admin else None
    return render(request, 'properties/property_form.html', {'investors': investors})


@login_required
def manage_staff(request):
    """Allows Investor or Admin to view and assign Receptionist staff to properties."""
    if not (request.user.is_admin or request.user.is_investor):
        messages.error(request, "Permission denied.")
        return redirect('dashboard:index')

    if request.user.is_admin:
        properties = Property.objects.filter(is_active=True)
        staff_members = PropertyStaff.objects.all().select_related('property', 'user')
        receptionists = CustomUser.objects.filter(role__in=['receptionist', 'accountant']).order_by('username')
    else:
        properties = Property.objects.filter(investor=request.user, is_active=True)
        staff_members = PropertyStaff.objects.filter(property__investor=request.user).select_related('property', 'user')
        receptionists = CustomUser.objects.filter(role__in=['receptionist', 'accountant']).filter(
            Q(property_assignments__property__investor=request.user) | Q(property_assignments__isnull=True)
        ).distinct().order_by('username')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign_existing':
            user_id = request.POST.get('user_id')
            property_id = request.POST.get('property_id')
            salary_val = Decimal(request.POST.get('base_salary', '0.00'))
            
            target_user = get_object_or_404(CustomUser, id=user_id, role__in=['receptionist', 'accountant'])
            target_prop = get_object_or_404(Property, id=property_id)
            
            if not request.user.is_admin and target_prop.investor != request.user:
                messages.error(request, "Permission denied.")
                return redirect('properties:staff')

            staff_obj, created = PropertyStaff.objects.get_or_create(
                property=target_prop,
                user=target_user,
                defaults={'role': target_user.role, 'base_salary': salary_val, 'is_active': True}
            )
            if not created:
                staff_obj.is_active = True
                staff_obj.role = target_user.role
                staff_obj.base_salary = salary_val
                staff_obj.save()

            messages.success(request, f"Staff member {target_user.username} assigned with Base Salary: {salary_val} ETB.")
            return redirect('properties:staff')

        elif action == 'create_new':
            username = request.POST.get('username')
            password = request.POST.get('password')
            email = request.POST.get('email', '')
            role_select = request.POST.get('role', 'receptionist')
            custom_role = request.POST.get('custom_role', '').strip()
            property_id = request.POST.get('property_id')
            salary_val = Decimal(request.POST.get('base_salary', '0.00'))

            if role_select == 'other' and custom_role:
                assigned_role = custom_role
                user_system_role = 'receptionist'
            else:
                assigned_role = role_select
                user_system_role = role_select if role_select in ['receptionist', 'accountant'] else 'receptionist'

            target_prop = get_object_or_404(Property, id=property_id)
            if not request.user.is_admin and target_prop.investor != request.user:
                messages.error(request, "Permission denied.")
                return redirect('properties:staff')

            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' already exists.")
                return redirect('properties:staff')

            new_user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=email,
                role=user_system_role
            )

            PropertyStaff.objects.create(
                property=target_prop,
                user=new_user,
                role=assigned_role,
                base_salary=salary_val,
                is_active=True
            )

            messages.success(request, f"Created staff account for '{new_user.username}' as '{assigned_role}' with Base Salary: {salary_val} ETB.")
            return redirect('properties:staff')

        elif action == 'update_salary':
            staff_id = request.POST.get('staff_id')
            salary_val = Decimal(request.POST.get('base_salary', '0.00'))
            staff_obj = get_object_or_404(PropertyStaff, id=staff_id)

            if not request.user.is_admin and staff_obj.property.investor != request.user:
                messages.error(request, "Permission denied.")
                return redirect('properties:staff')

            staff_obj.base_salary = salary_val
            staff_obj.save()
            messages.success(request, f"Updated salary for {staff_obj.user.username} to {salary_val} ETB.")
            return redirect('properties:staff')

    return render(request, 'properties/staff_management.html', {
        'properties': properties,
        'staff_members': staff_members,
        'receptionists': receptionists
    })


@login_required
def remove_staff(request, staff_id):
    staff_record = get_object_or_404(PropertyStaff, id=staff_id)
    if not (request.user.is_admin or staff_record.property.investor == request.user):
        messages.error(request, "Permission denied.")
        return redirect('dashboard:index')

    prop_name = staff_record.property.property_name
    username = staff_record.user.username
    staff_record.delete()
    messages.success(request, f"Removed Receptionist '{username}' from {prop_name}.")
    return redirect('properties:staff')
