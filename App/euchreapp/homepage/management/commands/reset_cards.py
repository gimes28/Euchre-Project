from django.core.management.base import BaseCommand
from homepage.models import Card

class Command(BaseCommand):
    help = 'Reset the deck to a full Euchre set'

    def handle(self, *args, **options):
        Card.objects.all().delete()
        for suit, _ in Card.SUITS:
            for rank, _ in Card.RANKS:
                Card.objects.create(suit=suit, rank=rank)
        self.stdout.write(self.style.SUCCESS('Deck reset successfully.'))
