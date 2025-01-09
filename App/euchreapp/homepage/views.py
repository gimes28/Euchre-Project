from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from random import shuffle
from .models import start_euchre_game, start_round, Game, Player, Card, deal_hand as model_deal_hand

# Render the homepage
def home(request):
    return render(request, "home.html")  # Reference the template in the root templates directory

# Signup and view to homepage and save the login information
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Automatically log in the user after signup
            return redirect('/')  # Redirect to the homepage
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

# Login redirects to homepage or the admin page if logging as admin
class CustomLoginView(LoginView):
    template_name = 'login.html'  # Use custom template in the root templates directory

    def get_success_url(self):
        # Redirect admin users to the admin site
        if self.request.user.is_staff or self.request.user.is_superuser:
            return '/admin/'
        # Redirect regular users to the default redirect URL
        return super().get_success_url()

@csrf_exempt
def start_new_game(request):
    if request.method == 'POST':
        game = Game.objects.create()
        dealt_cards, dealer, highest_card = start_round(game)  # Get highest_card from start_round

        # Ensure highest_card is properly serialized
        if highest_card:
            highest_card_info = f"{highest_card.rank} of {highest_card.suit}"
        else:
            highest_card_info = "No card"

        # Prepare the response
        response = {
            "dealt_cards": {player.name: f"{card.rank} of {card.suit}" for player, card in dealt_cards.items()},
            "dealer": dealer.name,
            "highest_card": highest_card_info,
        }
        return JsonResponse(response)
    return JsonResponse({"error": "Invalid request method."}, status=400)

@csrf_exempt
def deal_hand(request):
    if request.method == "POST":
        dealer_name = request.POST.get("dealer")
        dealer = Player.objects.get(name=dealer_name)
        players = Player.objects.all()

        # Shuffle the deck
        deck = list(Card.objects.all())
        shuffle(deck)

        # Use the model's `deal_hand` function to deal cards
        hands = model_deal_hand(deck, players)

        # Prepare the response
        response = {
            "hands": {
                player.name: [f"{card.rank} of {card.suit}" for card in hand]
                for player, hand in hands.items()
            }
        }
        return JsonResponse(response)

    return JsonResponse({"error": "Invalid request method."}, status=400)