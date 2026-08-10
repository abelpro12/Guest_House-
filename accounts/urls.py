from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('investors/', views.investors_list, name='investors'),
    path('investors/create/', views.create_investor, name='create_investor'),
    path('users/<int:user_id>/edit/', views.edit_user_account, name='edit_user'),
]
