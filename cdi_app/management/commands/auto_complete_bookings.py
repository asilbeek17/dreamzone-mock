from django.core.management.base import BaseCommand
from cdi_app.views import auto_complete_expired_bookings


class Command(BaseCommand):
    help = 'Mark accepted bookings as completed when 3 hours have passed since the test time'

    def handle(self, *args, **options):
        count = auto_complete_expired_bookings()
        if count:
            self.stdout.write(self.style.SUCCESS(f'Completed {count} booking(s).'))
        else:
            self.stdout.write('No bookings needed updating.')
