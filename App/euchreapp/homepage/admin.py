from django.contrib import admin

# Register your models here.
from .models import Game, Player, Hand, Card, PlayedCard, GameResult

# Register the Player model
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_human", "team", "partner")
    search_fields = ("name",)
    list_filter = ("is_human",)


# Register the Game model
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    search_fields = ("id",)


# Register the Hand model
@admin.register(Hand)
class HandAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "dealer", "trump_suit", "winner")
    list_filter = ("trump_suit",)
    autocomplete_fields = ("game", "dealer", "winner")
    search_fields = ("id", "game__id")  # Add a searchable field for the referenced `game`
    ordering = ("id",)



# Register the Card model
@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "rank", "suit", "is_trump")
    list_filter = ("suit", "is_trump")
    search_fields = ("rank", "suit")


# Register the PlayedCard model
@admin.register(PlayedCard)
class PlayedCardAdmin(admin.ModelAdmin):
    list_display = ("id", "hand", "player", "card", "order")
    autocomplete_fields = ("hand", "player", "card")
    list_filter = ("hand", "player")
    ordering = ("hand", "order")
    search_fields = ("hand__id", "player__name", "card__rank", "card__suit")


# Register the GameResult model
@admin.register(GameResult)
class GameResultAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "winner", "total_hands", "points")
    autocomplete_fields = ("game", "winner")
    ordering = ("-game",)
    search_fields = ("game__id", "winner__name")
    
    
class PlayedCardInline(admin.TabularInline):
    model = PlayedCard
    extra = 0
    
class HandAdmin(admin.ModelAdmin):
    inlines = [PlayedCardInline]