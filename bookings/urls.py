from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.booking_list, name='list'),
    path('create/', views.booking_create, name='create'),
    path('<int:booking_id>/', views.booking_detail, name='detail'),
    path('quick-check-in/', views.quick_check_in, name='quick_check_in'),
    path('<int:booking_id>/check-in/', views.check_in_booking, name='check_in'),
    path('<int:booking_id>/check-out/', views.perform_check_out, name='check_out'),
]
