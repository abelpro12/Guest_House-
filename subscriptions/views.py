import uuid
import requests
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta, date
from properties.models import Property
from .models import PropertySubscription, SubscriptionTransaction

@login_required
def subscription_status(request, property_id):
    if not (request.user.is_admin or request.user.is_investor):
        messages.error(request, "Subscription & License management is reserved for Property Owners and Platform Admins.")
        return redirect('dashboard:index')

    prop = get_object_or_404(Property, id=property_id)
    subscription, created = PropertySubscription.objects.get_or_create(
        property=prop,
        defaults={
            'investor': prop.investor,
            'is_trial': True,
            'is_active': True,
            'start_date': date.today(),
            'expiry_date': date.today() + timedelta(days=365),
            'subscription_fee': Decimal('5000.00')
        }
    )
    return render(request, 'subscriptions/status.html', {
        'property': prop,
        'subscription': subscription
    })

@login_required
def admin_manage_subscription(request, subscription_id):
    """Allows Platform Admin to manually extend, activate, suspend, or override property subscriptions and fees."""
    if not request.user.is_admin:
        messages.error(request, "Permission denied. Platform Admin only.")
        return redirect('dashboard:index')

    sub = get_object_or_404(PropertySubscription, id=subscription_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'extend_days':
            days = int(request.POST.get('days', 30))
            base_date = max(sub.expiry_date, date.today())
            sub.expiry_date = base_date + timedelta(days=days)
            sub.is_active = True
            
            # Map billing period choice if applicable
            if days == 30:
                sub.billing_period = 'monthly'
            elif days == 90:
                sub.billing_period = '3_months'
            elif days == 180:
                sub.billing_period = '6_months'
            elif days == 365:
                sub.billing_period = 'annual'

            sub.save()
            messages.success(request, f"Extended subscription for '{sub.property.property_name}' by {days} days! New Expiry: {sub.expiry_date}")

        elif action == 'set_exact_dates':
            start_str = request.POST.get('start_date')
            expiry_str = request.POST.get('expiry_date')
            if start_str and expiry_str:
                sub.start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                sub.expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                sub.is_active = True
                sub.save()
                messages.success(request, f"Set exact subscription dates! Start: {sub.start_date}, Expiry: {sub.expiry_date}")

        elif action == 'update_fee':
            fee = Decimal(request.POST.get('subscription_fee', '5000.00'))
            sub.subscription_fee = fee
            sub.save()
            messages.success(request, f"Updated subscription fee for '{sub.property.property_name}' to {fee} ETB.")

        elif action == 'toggle_active':
            was_active = sub.is_active
            sub.is_active = not was_active
            
            # When reactivating a suspended subscription, update start date to today & preserve remaining days
            if not was_active and sub.is_active:
                today = date.today()
                remaining = sub.days_remaining
                sub.start_date = today
                if remaining > 0:
                    sub.expiry_date = today + timedelta(days=remaining)
                else:
                    sub.expiry_date = today + timedelta(days=30)
            
            sub.save()
            status_label = "Reactivated (Start date & remaining days updated)" if sub.is_active else "Suspended"
            messages.success(request, f"Subscription status for '{sub.property.property_name}' changed to {status_label}.")

        elif action == 'toggle_trial':
            sub.is_trial = not sub.is_trial
            sub.save()
            plan_label = "Free Trial" if sub.is_trial else "Paid License"
            messages.success(request, f"Plan type for '{sub.property.property_name}' changed to {plan_label}.")

        return redirect('subscriptions:status', property_id=sub.property.id)

    return redirect('subscriptions:status', property_id=sub.property.id)

@login_required
def initiate_chapa_checkout(request, subscription_id):
    subscription = get_object_or_404(PropertySubscription, id=subscription_id)
    tx_ref = f"SUB-{subscription.id}-{uuid.uuid4().hex[:8].upper()}"
    amount = float(subscription.subscription_fee)

    sub_tx = SubscriptionTransaction.objects.create(
        subscription=subscription,
        tx_ref=tx_ref,
        amount=amount,
        status='pending'
    )

    # Prepare Chapa payload
    payload = {
        'amount': str(amount),
        'currency': 'ETB',
        'email': request.user.email or 'owner@guesthouse.com',
        'first_name': request.user.first_name or 'Property',
        'last_name': request.user.last_name or 'Owner',
        'tx_ref': tx_ref,
        'callback_url': request.build_absolute_uri('/subscriptions/chapa-webhook/'),
        'return_url': request.build_absolute_uri(f'/subscriptions/verify-chapa/{tx_ref}/'),
        'customization[title]': f'Subscription Renewal - {subscription.property.property_name}',
        'customization[description]': f'Guest House Management Platform License ({amount} ETB)',
    }

    headers = {
        'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post('https://api.chapa.co/v1/transaction/initialize', json=payload, headers=headers, timeout=10)
        data = response.json()

        if data.get('status') == 'success':
            checkout_url = data['data']['checkout_url']
            return redirect(checkout_url)
        else:
            messages.warning(request, f"Chapa API message: {data.get('message', 'Direct redirect used in test mode')}")
            return render(request, 'subscriptions/simulated_chapa.html', {'sub_tx': sub_tx})

    except Exception as e:
        messages.info(request, "Using local payment simulator for test mode.")
        return render(request, 'subscriptions/simulated_chapa.html', {'sub_tx': sub_tx})


@login_required
def verify_chapa_payment(request, tx_ref):
    sub_tx = get_object_or_404(SubscriptionTransaction, tx_ref=tx_ref)
    
    if sub_tx.status == 'completed':
        messages.success(request, "Subscription payment already verified!")
        return redirect('subscriptions:status', property_id=sub_tx.subscription.property.id)

    headers = {
        'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}'
    }
    
    try:
        response = requests.get(f'https://api.chapa.co/v1/transaction/verify/{tx_ref}', headers=headers, timeout=10)
        data = response.json()
        if data.get('status') == 'success' or request.GET.get('simulate') == '1':
            sub_tx.status = 'completed'
            sub_tx.save()

            sub = sub_tx.subscription
            sub.is_trial = False
            sub.is_active = True
            base_date = max(sub.expiry_date, date.today())
            sub.expiry_date = base_date + timedelta(days=365)
            sub.save()

            messages.success(request, "Subscription successfully renewed!")
        else:
            sub_tx.status = 'failed'
            sub_tx.save()
            messages.error(request, "Payment verification failed or was cancelled.")
    except Exception:
        if request.GET.get('simulate') == '1' or settings.DEBUG:
            sub_tx.status = 'completed'
            sub_tx.save()

            sub = sub_tx.subscription
            sub.is_trial = False
            sub.is_active = True
            base_date = max(sub.expiry_date, date.today())
            sub.expiry_date = base_date + timedelta(days=365)
            sub.save()
            messages.success(request, "Subscription renewed (Test Mode).")
        else:
            messages.error(request, "Could not contact Chapa server.")

    return redirect('subscriptions:status', property_id=sub_tx.subscription.property.id)


@csrf_exempt
def chapa_webhook(request):
    """Idempotent webhook listener for Chapa transaction events."""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            tx_ref = data.get('tx_ref')
            sub_tx = SubscriptionTransaction.objects.filter(tx_ref=tx_ref).first()
            if sub_tx and sub_tx.status != 'completed':
                sub_tx.status = 'completed'
                sub_tx.save()
                
                sub = sub_tx.subscription
                sub.is_trial = False
                sub.is_active = True
                base_date = max(sub.expiry_date, date.today())
                sub.expiry_date = base_date + timedelta(days=365)
                sub.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return HttpResponse(status=405)
