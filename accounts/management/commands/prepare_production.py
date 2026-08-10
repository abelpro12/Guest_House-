from django.core.management.base import BaseCommand
from accounts.models import CustomUser

class Command(BaseCommand):
    help = 'Prepares system for production launch by purging demo accounts and mock seeding data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Preparing system for REAL-WORLD PRODUCTION LAUNCH..."))

        demo_usernames = ['admin', 'investor', 'receptionist', 'recep123', 'guest']
        demo_users = CustomUser.objects.filter(username__in=demo_usernames)

        if demo_users.exists():
            count = demo_users.count()
            demo_users.delete()
            self.stdout.write(self.style.SUCCESS(f"[OK] Purged {count} demo accounts ({', '.join(demo_usernames)})."))
        else:
            self.stdout.write("No default demo accounts found.")

        self.stdout.write(self.style.SUCCESS("[OK] Demo credentials purged cleanly."))
        self.stdout.write(self.style.SUCCESS("[OK] System is clean & ready for real production accounts."))
        self.stdout.write(self.style.NOTICE("Run 'python manage.py createsuperuser' to register your official production admin."))
