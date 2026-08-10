from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AuditLog

@login_required
def audit_log_list(request):
    if not (request.user.is_admin or request.user.is_investor):
        messages.error(request, "Permission denied.")
        return redirect('dashboard:index')

    prop = getattr(request, 'current_property', None)
    if request.user.is_admin:
        logs = AuditLog.objects.all().order_by('-timestamp')[:500]
    else:
        logs = AuditLog.objects.filter(property=prop).order_by('-timestamp')[:500] if prop else AuditLog.objects.none()

    return render(request, 'audit/log_list.html', {'logs': logs})
