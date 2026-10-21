from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cards.models import CardInquiry, CardVisit


class Command(BaseCommand):
    help = "Remove old anonymous visit records (90 days) and inquiries (180 days)."

    def handle(self, *args, **options):
        now = timezone.now()
        visits, _ = CardVisit.objects.filter(visited_at__lt=now - timedelta(days=90)).delete()
        inquiries, _ = CardInquiry.objects.filter(created_at__lt=now - timedelta(days=180)).delete()
        self.stdout.write(f"Removed {visits} visits and {inquiries} inquiries.")
