from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Guest
from accounts.models import CustomUser
from properties.utils import get_current_property
from config.permissions import staff_required

@login_required
@staff_required
def guest_list(request):
    query = request.GET.get('q', '').strip()
    prop = get_current_property(request)

    if prop:
        guests_qs = Guest.objects.filter(Q(property=prop) | Q(bookings__property=prop) | Q(property__isnull=True)).distinct().order_by('-created_at')
    else:
        guests_qs = Guest.objects.all().order_by('-created_at')

    if query:
        guests_qs = guests_qs.filter(
            Q(full_name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(id_document_number__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(guests_qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'guests/guest_list.html', {
        'guests': page_obj,
        'page_obj': page_obj,
        'current_property': prop,
        'query': query
    })

@login_required
@staff_required
def guest_create(request):
    prop = get_current_property(request)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        id_doc_type = request.POST.get('id_document_type', 'national_id')
        id_doc_num = request.POST.get('id_document_number', '').strip()
        nationality = request.POST.get('nationality', 'Ethiopian').strip()
        address = request.POST.get('address', '').strip()
        id_photo = request.FILES.get('id_photo')
        create_user_account = request.POST.get('create_user_account') == '1'

        if not full_name or not phone_number or not id_doc_num:
            messages.error(request, "Full Name, Phone Number, and ID Document Number are required fields.")
            return render(request, 'guests/guest_form.html')

        user_account = None
        if create_user_account:
            custom_username = request.POST.get('guest_username', '').strip()
            custom_password = request.POST.get('guest_password', '').strip() or 'Guest@1234'
            
            username = custom_username or phone_number or id_doc_num

            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' is already taken. Please enter a unique username.")
                return render(request, 'guests/guest_form.html')

            user_account = CustomUser.objects.create_user(
                username=username,
                password=custom_password,
                email=email or '',
                first_name=full_name.split()[0] if full_name else '',
                role='guest'
            )

        guest = Guest.objects.create(
            property=prop,
            user=user_account,
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            id_document_type=id_doc_type,
            id_document_number=id_doc_num,
            id_photo=id_photo,
            nationality=nationality,
            address=address
        )
        messages.success(request, f"Guest '{guest.full_name}' registered successfully!")
        
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('guests:detail', guest_id=guest.id)

    return render(request, 'guests/guest_form.html')

@login_required
@staff_required
def guest_detail(request, guest_id):
    guest = get_object_or_404(Guest, id=guest_id)
    bookings = guest.bookings.all().order_by('-created_at')
    return render(request, 'guests/guest_detail.html', {
        'guest': guest,
        'bookings': bookings
    })

@login_required
@staff_required
def provision_guest_account(request, guest_id):
    """Provisions a new portal login account or updates credentials for an existing guest."""
    guest = get_object_or_404(Guest, id=guest_id)
    
    if request.method == 'POST':
        custom_username = request.POST.get('guest_username', '').strip()
        custom_password = request.POST.get('guest_password', '').strip()

        username = custom_username or guest.phone_number or guest.id_document_number

        if not username:
            messages.error(request, "A valid username or phone number is required to provision account.")
            return redirect('guests:detail', guest_id=guest.id)

        # Check username uniqueness
        existing_user = CustomUser.objects.filter(username=username).exclude(id=guest.user.id if guest.user else None).first()
        if existing_user:
            messages.error(request, f"Username '{username}' is already taken by another account. Please enter a different username.")
            return redirect('guests:detail', guest_id=guest.id)

        if guest.user:
            # Update existing user account
            guest.user.username = username
            if custom_password:
                guest.user.set_password(custom_password)
            guest.user.save()
            messages.success(request, f"Successfully updated login credentials for '{guest.full_name}'! Username: @{username}")
        else:
            # Provision brand new user account
            password = custom_password or 'Guest@1234'
            user_account = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=guest.email or '',
                first_name=guest.full_name.split()[0] if guest.full_name else '',
                role='guest'
            )
            guest.user = user_account
            guest.save()
            messages.success(request, f"Successfully provisioned Guest Portal account for '{guest.full_name}'! Username: @{username}")

    return redirect('guests:detail', guest_id=guest.id)

@login_required
@staff_required
def guest_edit(request, guest_id):
    """Allows Receptionists, Investors, and Admins to edit profile and login credentials for an existing guest."""
    guest = get_object_or_404(Guest, id=guest_id)

    if request.method == 'POST':
        guest.full_name = request.POST.get('full_name', guest.full_name).strip()
        guest.phone_number = request.POST.get('phone_number', guest.phone_number).strip()
        guest.email = request.POST.get('email', guest.email).strip()
        guest.id_document_type = request.POST.get('id_document_type', guest.id_document_type)
        guest.id_document_number = request.POST.get('id_document_number', guest.id_document_number).strip()
        guest.nationality = request.POST.get('nationality', guest.nationality).strip()
        guest.address = request.POST.get('address', guest.address).strip()
        
        if request.FILES.get('id_photo'):
            guest.id_photo = request.FILES['id_photo']
            
        guest.save()

        # Handle portal user account updates if requested
        create_user_account = request.POST.get('create_user_account') == '1'
        if create_user_account or guest.user:
            custom_username = request.POST.get('guest_username', '').strip()
            custom_password = request.POST.get('guest_password', '').strip()

            username = custom_username or guest.phone_number or guest.id_document_number

            if username:
                # Check uniqueness
                existing_user = CustomUser.objects.filter(username=username).exclude(id=guest.user.id if guest.user else None).first()
                if existing_user:
                    messages.error(request, f"Username '{username}' is already taken by another user.")
                    return render(request, 'guests/guest_form.html', {'guest': guest})

                if guest.user:
                    guest.user.username = username
                    if custom_password:
                        guest.user.set_password(custom_password)
                    guest.user.save()
                else:
                    password = custom_password or 'Guest@1234'
                    user_account = CustomUser.objects.create_user(
                        username=username,
                        password=password,
                        email=guest.email or '',
                        first_name=guest.full_name.split()[0] if guest.full_name else '',
                        role='guest'
                    )
                    guest.user = user_account
                    guest.save()

        messages.success(request, f"Successfully updated profile and credentials for '{guest.full_name}'!")
        return redirect('guests:detail', guest_id=guest.id)

    return render(request, 'guests/guest_form.html', {'guest': guest})
