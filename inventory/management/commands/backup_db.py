from django.core.management.base import BaseCommand
from django.core import management
from datetime import datetime
import os
import cloudinary
import cloudinary.uploader

class Command(BaseCommand):
    help = 'Backup database and upload to Cloudinary'

    def handle(self, *args, **kwargs):
        # Timestamp for the backup file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_{timestamp}.json'

        # Create the backup
        with open(backup_file, 'w') as f:
            management.call_command('dumpdata', exclude=['contenttypes', 'auth.permission'], indent=2, stdout=f)

        # Upload to Cloudinary
        try:
            result = cloudinary.uploader.upload(
                backup_file,
                resource_type="raw",
                public_id=f"backups/{backup_file}",
                tags=['backup', 'database']
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created and uploaded backup: {result["secure_url"]}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to upload backup: {str(e)}')
            )
        finally:
            # Clean up local backup file
            if os.path.exists(backup_file):
                os.remove(backup_file)