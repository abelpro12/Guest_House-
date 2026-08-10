from django.urls import path
from . import views

app_name = 'shifts'

urlpatterns = [
    path('', views.shift_list, name='list'),
    path('start/', views.start_shift, name='start'),
    path('<int:shift_id>/close/', views.close_shift, name='close'),
]
