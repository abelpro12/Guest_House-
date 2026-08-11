from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from .models import Room, RoomType
from properties.models import Property
from config.permissions import staff_required, investor_or_admin_required

@login_required
@staff_required
def room_list(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Please select a property first.")
        return redirect('properties:list')

    rooms_qs = Room.objects.filter(property=prop, is_active=True).select_related('room_type')
    room_types = RoomType.objects.all()

    # Filter params
    status_filter = request.GET.get('status')
    if status_filter:
        rooms_qs = rooms_qs.filter(status=status_filter)

    paginator = Paginator(rooms_qs, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'rooms/room_list.html', {
        'rooms': page_obj,
        'page_obj': page_obj,
        'room_types': room_types,
        'current_status': status_filter
    })

@login_required
@investor_or_admin_required
def room_create(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "No active property selected.")
        return redirect('properties:list')

    if request.method == 'POST':
        room_number = request.POST.get('room_number', '').strip()
        room_type_id = request.POST.get('room_type_id')
        price_per_night = request.POST.get('price_per_night')
        status = request.POST.get('status', 'vacant')

        if not room_number:
            messages.error(request, "Room number is required.")
            return redirect('rooms:list')

        if Room.objects.filter(property=prop, room_number=room_number).exists():
            messages.error(request, f"Room number '{room_number}' already exists for this property.")
            return redirect('rooms:list')

        room_type = get_object_or_404(RoomType, id=room_type_id)

        Room.objects.create(
            property=prop,
            room_number=room_number,
            room_type=room_type,
            price_per_night=Decimal(price_per_night) if price_per_night else room_type.default_price,
            status=status
        )
        messages.success(request, f"Room {room_number} created successfully.")
        return redirect('rooms:list')

    return redirect('rooms:list')


@login_required
@investor_or_admin_required
def bulk_create_rooms(request):
    """Allows Super Admin or Investor to generate multiple rooms at once."""
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "No active property selected.")
        return redirect('properties:list')

    if request.method == 'POST':
        room_type_id = request.POST.get('room_type_id')
        prefix = request.POST.get('prefix', '').strip()
        start_number = int(request.POST.get('start_number', 1))
        count = int(request.POST.get('count', 1))
        price_per_night = request.POST.get('price_per_night')

        room_type = get_object_or_404(RoomType, id=room_type_id)
        price = Decimal(price_per_night) if price_per_night else room_type.default_price

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for i in range(count):
                current_num = start_number + i
                room_num_str = f"{prefix}{current_num}"
                
                if Room.objects.filter(property=prop, room_number=room_num_str).exists():
                    skipped_count += 1
                else:
                    Room.objects.create(
                        property=prop,
                        room_number=room_num_str,
                        room_type=room_type,
                        price_per_night=price,
                        status='vacant'
                    )
                    created_count += 1

        if created_count > 0:
            messages.success(request, f"Successfully created {created_count} room(s) for {prop.property_name}!")
        if skipped_count > 0:
            messages.warning(request, f"Skipped {skipped_count} room(s) that already existed.")

        return redirect('rooms:list')

    return redirect('rooms:list')


@login_required
@staff_required
def update_room_status(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Room.STATUS_CHOICES):
            room.status = new_status
            room.save()
            
            from audit.models import AuditLog
            AuditLog.log_action(
                user=request.user,
                property=room.property,
                action='update_room_status',
                model_name='Room',
                object_id=str(room.id),
                new_value=new_status
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'new_status': room.get_status_display()})
            messages.success(request, f"Room {room.room_number} status changed to {room.get_status_display()}.")
    return redirect('rooms:list')
