from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('status/<int:property_id>/', views.subscription_status, name='status'),
    path('admin-manage/<int:subscription_id>/', views.admin_manage_subscription, name='admin_manage'),
    path('checkout/<int:subscription_id>/', views.initiate_chapa_checkout, name='checkout'),
    path('verify-chapa/<str:tx_ref>/', views.verify_chapa_payment, name='verify_chapa'),
    path('chapa-webhook/', views.chapa_webhook, name='chapa_webhook'),
]
