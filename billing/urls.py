from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.invoice_list, name='list'),
    path('<int:invoice_id>/', views.invoice_detail, name='detail'),
    path('<int:invoice_id>/add-item/', views.add_invoice_item, name='add_item'),
]
