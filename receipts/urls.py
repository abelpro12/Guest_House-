from django.urls import path
from . import views

app_name = 'receipts'

urlpatterns = [
    path('<int:receipt_id>/', views.receipt_detail, name='detail'),
    path('<int:receipt_id>/pdf/', views.receipt_pdf, name='pdf'),
    path('<int:receipt_id>/void/', views.void_receipt, name='void'),
]
