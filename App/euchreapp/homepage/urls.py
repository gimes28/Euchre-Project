from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),  # Homepage view
    path('start-game/', views.start_new_game, name='start_game'),  # Start a new game
    path('deal-hand/', views.deal_hand, name='deal_hand'),  # Deal cards for the first round
    path('deal-next-hand/', views.deal_next_hand, name='deal_next_hand'),  # Handle subsequent rounds
    path('pick-trump/', views.pick_trump, name='pick_trump'),  # Request trump card decision
    path('accept-trump/', views.accept_trump, name='accept_trump'),  # Handle accepting the trump card
    path('reset-game/', views.reset_game, name='reset_game'),  # Reset the game
    path('start-round/', views.start_round, name='start_round'),  # Start a new round
    # path('play-card/', views.play_human_card, name='play_card'), # Player plays card
    path('get-game-score/', views.get_game_score, name='get_game_score'),  # Update game score at end of round
    path('get-remaining-cards/', views.get_remaining_cards, name='get_remaining_cards'),
    path('play-next-trick/', views.play_next_trick, name='play_next_trick'),
    path('determine-trump/', views.determine_bot_trump_decision, name='determine_trump'),
]