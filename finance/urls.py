from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_dashboard, name='dashboard'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/create/', views.payroll_create, name='payroll_create'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/log/', views.attendance_log, name='attendance_log'),
    path('attendance/bulk/', views.attendance_bulk_mark, name='attendance_bulk'),
]
