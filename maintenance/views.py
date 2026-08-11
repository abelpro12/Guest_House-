from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .models import MaintenanceTicket
from rooms.models import Room
from audit.models import AuditLog
from config.permissions import staff_required

@login_required
@staff_required
def ticket_list(request):
    prop = getattr(request, 'current_property', None)
    tickets_qs = MaintenanceTicket.objects.filter(property=prop).select_related('room', 'reported_by').order_by('-created_at') if prop else MaintenanceTicket.objects.none()
    
    paginator = Paginator(tickets_qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'maintenance/ticket_list.html', {
        'tickets': page_obj,
        'page_obj': page_obj
    })

@login_required
@staff_required
def ticket_create(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Select property.")
        return redirect('properties:list')

    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        description = request.POST.get('description', '').strip()
        priority = request.POST.get('priority', 'medium')
        cost = Decimal(request.POST.get('cost', '0.00'))

        room = get_object_or_404(Room, id=room_id, property=prop)
        
        # Lock room for maintenance
        room.status = 'maintenance'
        room.save()

        ticket = MaintenanceTicket.objects.create(
            property=prop,
            room=room,
            reported_by=request.user,
            description=description,
            priority=priority,
            cost=cost,
            status='open'
        )

        AuditLog.log_action(
            user=request.user,
            property=prop,
            action='report_maintenance',
            model_name='MaintenanceTicket',
            object_id=str(ticket.id),
            new_value=f"Locked Room {room.room_number} for Maintenance"
        )

        messages.success(request, f"Maintenance ticket logged for Room {room.room_number}. Room locked for booking.")
        return redirect('maintenance:list')

    rooms = Room.objects.filter(property=prop, is_active=True)
    return render(request, 'maintenance/ticket_form.html', {'rooms': rooms})

@login_required
@staff_required
def ticket_update_status(request, ticket_id):
    ticket = get_object_or_404(MaintenanceTicket, id=ticket_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        ticket.status = new_status
        if new_status in ['resolved', 'closed']:
            ticket.completion_date = timezone.now().date()
            # Restore room to vacant
            ticket.room.status = 'vacant'
            ticket.room.save()

            AuditLog.log_action(
                user=request.user,
                property=ticket.property,
                action='resolve_maintenance',
                model_name='MaintenanceTicket',
                object_id=str(ticket.id),
                new_value=f"Resolved ticket. Room {ticket.room.room_number} restored to Vacant"
            )

        ticket.save()
        messages.success(request, f"Maintenance ticket status updated to {ticket.get_status_display()}.")
    return redirect('maintenance:list')
