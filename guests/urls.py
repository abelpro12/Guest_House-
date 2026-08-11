from django.urls import path
from . import views

app_name = 'guests'

urlpatterns = [
    path('', views.guest_list, name='list'),
    path('create/', views.guest_create, name='create'),
    path('<int:guest_id>/', views.guest_detail, name='detail'),
    path('<int:guest_id>/account/', views.provision_guest_account, name='provision_account'),
]
