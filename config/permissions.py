"""
Role-based permission decorators for the Guest House Management System.
Use these decorators on views to enforce access control beyond @login_required.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def role_required(*allowed_roles):
    """
    Decorator that restricts view access to users with specified roles.
    Admin and superuser always pass.
    
    Usage:
        @login_required
        @role_required('investor', 'admin')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.role == 'admin':
                return view_func(request, *args, **kwargs)
            if user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access this page.")
            return redirect('dashboard:index')
        return _wrapped_view
    return decorator


def investor_or_admin_required(view_func):
    """Shortcut: Only investor, accountant, or admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.role in ('admin', 'investor', 'accountant'):
            return view_func(request, *args, **kwargs)
        messages.error(request, "This section requires Investor or Admin access.")
        return redirect('dashboard:index')
    return _wrapped_view


def staff_required(view_func):
    """Shortcut: Investor, receptionist, accountant, or admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.role in ('admin', 'investor', 'accountant', 'receptionist'):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Staff access required.")
        return redirect('dashboard:index')
    return _wrapped_view


def admin_only(view_func):
    """Shortcut: Only platform admin or superuser."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.role == 'admin':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Platform Admin access required.")
        return redirect('dashboard:index')
    return _wrapped_view
