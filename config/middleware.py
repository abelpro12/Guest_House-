import threading
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

_thread_locals = threading.local()

def get_current_request():
    return getattr(_thread_locals, 'request', None)

def get_current_user():
    req = get_current_request()
    if req and hasattr(req, 'user') and req.user.is_authenticated:
        return req.user
    return None

class AuditMiddleware:
    """Captures request for audit logging threadlocal storage."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        _thread_locals.request = None
        return response


class PropertyScopingMiddleware:
    """
    Middleware that runs BEFORE view execution to resolve the active Property for the request
    and attach `request.current_property`.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            from properties.models import Property, PropertyStaff
            from bookings.models import Booking

            user = request.user
            selected_property_id = request.session.get('selected_property_id')
            current_prop = None

            if selected_property_id:
                if user.is_admin:
                    current_prop = Property.objects.filter(id=selected_property_id, is_active=True).first()
                elif user.is_investor:
                    current_prop = Property.objects.filter(id=selected_property_id, investor=user, is_active=True).first()
                elif user.is_receptionist:
                    if PropertyStaff.objects.filter(property_id=selected_property_id, user=user, is_active=True).exists():
                        current_prop = Property.objects.filter(id=selected_property_id, is_active=True).first()
                elif user.is_guest:
                    current_prop = Property.objects.filter(id=selected_property_id, is_active=True).first()

            if not current_prop:
                if user.is_admin:
                    current_prop = Property.objects.filter(is_active=True).first()
                elif user.is_investor:
                    current_prop = Property.objects.filter(investor=user, is_active=True).first()
                elif user.is_receptionist:
                    staff_record = PropertyStaff.objects.filter(user=user, is_active=True).select_related('property').first()
                    if staff_record:
                        current_prop = staff_record.property
                    else:
                        # Fallback for receptionist if not explicitly assigned in PropertyStaff: select first active property
                        current_prop = Property.objects.filter(is_active=True).first()
                        if current_prop:
                            PropertyStaff.objects.get_or_create(property=current_prop, user=user, defaults={'role': 'receptionist'})
                elif user.is_guest:
                    booking = Booking.objects.filter(guest__user=user, status='checked_in').select_related('property').first()
                    if booking:
                        current_prop = booking.property
                    else:
                        current_prop = Property.objects.filter(is_active=True).first()

            if current_prop:
                request.session['selected_property_id'] = current_prop.id
                request.current_property = current_prop
            else:
                request.current_property = None
        else:
            request.current_property = None

        return self.get_response(request)


class SubscriptionValidationMiddleware:
    """
    Checks if property subscription has expired.
    Blocks operational endpoints server-side if expired, while leaving authentication,
    subscription renewal, and static files accessible.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Allow superusers, admins, and static/media/subscriptions/auth routes
        path = request.path
        if (request.user.role == 'admin' or 
            path.startswith('/accounts/') or 
            path.startswith('/subscriptions/') or 
            path.startswith('/django-admin/') or 
            path.startswith('/static/') or 
            path.startswith('/media/')):
            return self.get_response(request)

        # Check property investor status and subscription status for Investor / Receptionist / Guest
        active_property = getattr(request, 'current_property', None)
        if active_property:
            if active_property.investor and not active_property.investor.is_active:
                if hasattr(active_property, 'subscription') and active_property.subscription:
                    return redirect(reverse('subscriptions:status', kwargs={'property_id': active_property.id}))
                return redirect('properties:list')

            if hasattr(active_property, 'subscription'):
                sub = active_property.subscription
                if sub and (not sub.is_active or sub.expiry_date < timezone.now().date()):
                    # Redirect to subscription page with warning
                    return redirect(reverse('subscriptions:status', kwargs={'property_id': active_property.id}))

        return self.get_response(request)
