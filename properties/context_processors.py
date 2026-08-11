from .models import Property

def current_property_processor(request):
    current_prop = getattr(request, 'current_property', None)
    user_properties = []

    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        if user.is_admin:
            user_properties = Property.objects.filter(is_active=True)
        elif user.is_investor:
            user_properties = Property.objects.filter(investor=user, is_active=True)
        elif user.is_receptionist:
            user_properties = Property.objects.filter(staff_members__user=user, is_active=True)

    site_language = request.session.get('site_language', 'en')
    return {
        'current_property': current_prop,
        'user_properties': user_properties,
        'current_language': site_language
    }
