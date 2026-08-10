from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Guest
from accounts.models import CustomUser

@login_required
def guest_list(request):
    query = request.GET.get('q', '')
    guests = Guest.objects.all().order_by('-created_at')

    if query:
        guests = guests.filter(
            Q(full_name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(id_document_number__icontains=query) |
            Q(email__icontains=query)
        )

    return render(request, 'guests/guest_list.html', {
        'guests': guests,
        'query': query
    })

@login_required
def guest_create(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        id_doc_type = request.POST.get('id_document_type')
        id_doc_num = request.POST.get('id_document_number')
        nationality = request.POST.get('nationality', 'Ethiopian')
        address = request.POST.get('address')
        create_user_account = request.POST.get('create_user_account') == '1'

        user_account = None
        if create_user_account:
            username = phone_number or id_doc_num
            user_account, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': email or '',
                    'first_name': full_name.split()[0] if full_name else '',
                    'role': 'guest'
                }
            )
            if created:
                user_account.set_password('Guest@1234')
                user_account.save()

        guest = Guest.objects.create(
            user=user_account,
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            id_document_type=id_doc_type,
            id_document_number=id_doc_num,
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
def guest_detail(request, guest_id):
    guest = get_object_or_404(Guest, id=guest_id)
    bookings = guest.bookings.all().order_by('-created_at')
    return render(request, 'guests/guest_detail.html', {
        'guest': guest,
        'bookings': bookings
    })
