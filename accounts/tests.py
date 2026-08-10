from django.test import TestCase
from accounts.models import CustomUser

class AccountsModelTests(TestCase):
    def test_create_user_with_roles(self):
        admin = CustomUser.objects.create_user(username='admin_test', password='pass', role='admin')
        investor = CustomUser.objects.create_user(username='investor_test', password='pass', role='investor')
        receptionist = CustomUser.objects.create_user(username='recep_test', password='pass', role='receptionist')
        guest = CustomUser.objects.create_user(username='guest_test', password='pass', role='guest')

        self.assertTrue(admin.is_admin)
        self.assertTrue(investor.is_investor)
        self.assertTrue(receptionist.is_receptionist)
        self.assertTrue(guest.is_guest)

    def test_admin_dashboard_access(self):
        admin = CustomUser.objects.create_user(username='admin_dash', password='pass', role='admin')
        self.client.force_login(admin)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Platform Administrator Panel")
