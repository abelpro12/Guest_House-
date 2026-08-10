from datetime import date, timedelta
from django.test import TestCase
from accounts.models import CustomUser
from properties.models import Property
from subscriptions.models import PropertySubscription

class SubscriptionAdminTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(username='admin_sub', password='p', role='admin')
        self.investor = CustomUser.objects.create_user(username='inv_sub', password='p', role='investor')
        self.prop = Property.objects.create(property_name='Lodge Sub', address='A', phone='1', email='a@a.com', investor=self.investor)
        self.sub = PropertySubscription.objects.create(
            property=self.prop,
            investor=self.investor,
            is_trial=True,
            is_active=True,
            start_date=date.today(),
            expiry_date=date.today() + timedelta(days=365)
        )

    def test_admin_subscription_override(self):
        self.client.force_login(self.admin)
        
        # Test extending subscription
        response = self.client.post(f'/subscriptions/admin-manage/{self.sub.id}/', {
            'action': 'extend_days',
            'days': '30'
        })
        self.assertEqual(response.status_code, 302)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.expiry_date, date.today() + timedelta(days=395))

        # Test toggle active
        response2 = self.client.post(f'/subscriptions/admin-manage/{self.sub.id}/', {
            'action': 'toggle_active'
        })
        self.assertEqual(response2.status_code, 302)
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.is_active)
