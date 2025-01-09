from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),  # Homepage view
    path('start-game/', views.start_new_game, name='start_game'),  # Start a new game
    path('deal-hand/', views.deal_hand, name='deal_hand'),  # Deal cards for a round
    path('pick-trump/', views.pick_trump, name='pick_trump'),  # Request trump card decision
    path('accept-trump/', views.accept_trump, name='accept_trump'),  # Handle accepting the trump card
    path('reset-game/', views.reset_game, name='reset_game'), # Reset the game on refresh
]