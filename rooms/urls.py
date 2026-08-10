from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    path('', views.room_list, name='list'),
    path('create/', views.room_create, name='create'),
    path('bulk-create/', views.bulk_create_rooms, name='bulk_create'),
    path('<int:room_id>/status/', views.update_room_status, name='update_status'),
]
