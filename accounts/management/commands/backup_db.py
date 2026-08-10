import os
import sys
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Executes database backup and outputs timestamped backup file for recovery.'

    def handle(self, *args, **options):
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"db_backup_{timestamp}.json"
        filepath = os.path.join(backup_dir, filename)

        self.stdout.write(f"Starting database backup to {filepath}...")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            call_command('dumpdata', '--natural-foreign', '--natural-primary', exclude=['contenttypes', 'auth.Permission'], stdout=f)

        self.stdout.write(self.style.SUCCESS(f"[OK] Backup completed successfully: {filepath}"))
        self.stdout.write(self.style.NOTICE("To restore this backup: python manage.py loaddata " + filepath))
