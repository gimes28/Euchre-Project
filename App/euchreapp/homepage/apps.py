from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_players(sender, **kwargs):
    from .models import Player

    if Player.objects.count() == 0:
        Player.objects.create(name="Player", is_human=True)
        Player.objects.create(name="Opponent1", is_human=False)
        Player.objects.create(name="Team Mate", is_human=False)
        Player.objects.create(name="Opponent2", is_human=False)


class HomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'homepage'

    def ready(self):
        post_migrate.connect(create_players, sender=self)
