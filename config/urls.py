from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from finance import views as finance_views

def root_redirect(request):
    return redirect('dashboard:index')

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', root_redirect, name='root'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('properties/', include('properties.urls', namespace='properties')),
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    path('rooms/', include('rooms.urls', namespace='rooms')),
    path('guests/', include('guests.urls', namespace='guests')),
    path('bookings/', include('bookings.urls', namespace='bookings')),
    path('billing/', include('billing.urls', namespace='billing')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('receipts/', include('receipts.urls', namespace='receipts')),
    path('shifts/', include('shifts.urls', namespace='shifts')),
    path('housekeeping/', include('housekeeping.urls', namespace='housekeeping')),
    path('maintenance/', include('maintenance.urls', namespace='maintenance')),
    path('attendance/', finance_views.attendance_list, name='attendance_direct'),
    path('finance/', include('finance.urls', namespace='finance')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('audit/', include('audit.urls', namespace='audit')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
