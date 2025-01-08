from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),  # Homepage view
    path('start-game/', views.start_game_view, name='start_game'), # Start new game
]