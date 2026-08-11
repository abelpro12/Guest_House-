from properties.models import Property

def get_current_property(request):
    prop_id = request.GET.get('property_id')
    if prop_id:
        p = Property.objects.filter(id=prop_id).first()
        if p:
            request.session['current_property_id'] = p.id
            return p

    session_prop_id = request.session.get('current_property_id')
    if session_prop_id:
        p = Property.objects.filter(id=session_prop_id).first()
        if p:
            return p

    if hasattr(request, 'current_property') and request.current_property:
        return request.current_property

    return Property.objects.first()
