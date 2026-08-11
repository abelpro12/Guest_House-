from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('receptionist/', views.receptionist_dashboard, name='receptionist'),
    path('investor/', views.investor_dashboard, name='investor'),
    path('admin-panel/', views.admin_dashboard, name='admin'),
    path('guest-portal/', views.guest_portal, name='guest_portal'),
    path('search/', views.global_search, name='search'),
    path('language/<str:lang_code>/', views.switch_language, name='switch_language'),
]
