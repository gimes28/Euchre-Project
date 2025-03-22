from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_players(sender, **kwargs):
    from .models import Player

    player_configs = [
        {"name": "Player", "is_human": True, "team": 1, "partner": "Team Mate"},
        {"name": "Opponent1", "is_human": False, "team": 2, "partner": "Opponent2"},
        {"name": "Team Mate", "is_human": False, "team": 1, "partner": "Player"},
        {"name": "Opponent2", "is_human": False, "team": 2, "partner": "Opponent1"}
    ]

    for config in player_configs:
        player, created = Player.objects.get_or_create(
            name=config["name"],
            defaults={
                "is_human": config["is_human"],
                "team": config["team"],
                "partner": config["partner"]
            }
        )

        if not created and (
            player.team == 0 or not player.partner
        ):
            player.team = config["team"]
            player.partner = config["partner"]
            player.save()

    # if Player.objects.count() == 0:
    #     Player.objects.create(name="Player", is_human=True, team=1, partner="Team Mate")
    #     Player.objects.create(name="Opponent1", is_human=False, team=2, partner="Opponent2")
    #     Player.objects.create(name="Team Mate", is_human=False, team=1, partner="Player")
    #     Player.objects.create(name="Opponent2", is_human=False, team=2, partner="Opponent1")


class HomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'homepage'

    def ready(self):
        post_migrate.connect(create_players, sender=self)
