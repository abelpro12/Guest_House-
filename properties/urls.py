from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    path('', views.list_properties, name='list'),
    path('create/', views.create_property, name='create'),
    path('select/<int:property_id>/', views.select_property, name='select'),
    path('staff/', views.manage_staff, name='staff'),
    path('staff/<int:staff_id>/remove/', views.remove_staff, name='remove_staff'),
]
