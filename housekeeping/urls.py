from django.urls import path
from . import views

app_name = 'housekeeping'

urlpatterns = [
    path('', views.housekeeping_list, name='list'),
    path('create/', views.task_create, name='create'),
    path('<int:task_id>/status/', views.task_update_status, name='update_status'),
]
