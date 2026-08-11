from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .models import HousekeepingTask
from rooms.models import Room
from audit.models import AuditLog
from config.permissions import staff_required

@login_required
@staff_required
def housekeeping_list(request):
    prop = getattr(request, 'current_property', None)
    tasks_qs = HousekeepingTask.objects.filter(property=prop).select_related('room', 'assigned_to').order_by('-created_at') if prop else HousekeepingTask.objects.none()
    cleaning_rooms = Room.objects.filter(property=prop, status='cleaning') if prop else Room.objects.none()
    
    paginator = Paginator(tasks_qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'housekeeping/task_list.html', {
        'tasks': page_obj,
        'page_obj': page_obj,
        'cleaning_rooms': cleaning_rooms
    })

@login_required
@staff_required
def task_create(request):
    prop = getattr(request, 'current_property', None)
    if not prop:
        messages.error(request, "Select property.")
        return redirect('properties:list')

    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        description = request.POST.get('task_description', '').strip()
        priority = request.POST.get('priority', 'medium')

        room = get_object_or_404(Room, id=room_id, property=prop)
        
        # Set room status to cleaning
        room.status = 'cleaning'
        room.save()

        task = HousekeepingTask.objects.create(
            property=prop,
            room=room,
            task_description=description or f"Clean Room {room.room_number}",
            priority=priority,
            status='pending'
        )

        messages.success(request, f"Housekeeping task created for Room {room.room_number}.")
        return redirect('housekeeping:list')

    rooms = Room.objects.filter(property=prop, is_active=True)
    return render(request, 'housekeeping/task_form.html', {'rooms': rooms})

@login_required
@staff_required
def task_update_status(request, task_id):
    task = get_object_or_404(HousekeepingTask, id=task_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        task.status = new_status
        if new_status == 'completed':
            task.completed_at = timezone.now()
            # Mark room as vacant/ready
            task.room.status = 'vacant'
            task.room.save()

            AuditLog.log_action(
                user=request.user,
                property=task.property,
                action='complete_cleaning',
                model_name='HousekeepingTask',
                object_id=str(task.id),
                new_value=f"Room {task.room.room_number} set to Vacant"
            )

        task.save()
        messages.success(request, f"Task status updated to {task.get_status_display()}.")
    return redirect('housekeeping:list')
