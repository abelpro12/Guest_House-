from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.transaction_list, name='list'),
    path('record/<int:booking_id>/', views.record_payment, name='record'),
    path('void/<int:transaction_id>/', views.void_transaction, name='void'),
]
