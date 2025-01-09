from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from random import shuffle
from .models import start_euchre_game, start_round, Game, Player, Card, deal_hand as model_deal_hand, PlayedCard

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
        # Step 1: Start a new game
        players = Player.objects.all()

        # Initialize the game and shuffle the deck
        game = Game.objects.create()
        deck = list(Card.objects.all())
        shuffle(deck)

        # Step 2: Determine the dealer based on the highest card
        if len(deck) < len(players):
            return JsonResponse({"error": "Not enough cards in the deck to determine the dealer."}, status=400)

        dealt_cards = {}
        for player in players:
            card = deck.pop()
            dealt_cards[player] = card

        # Find the highest card
        def card_rank_value(card):
            rank_order = ['9', '10', 'J', 'Q', 'K', 'A']
            return rank_order.index(card.rank)

        highest_card = max(dealt_cards.values(), key=card_rank_value)
        dealer = next(player for player, card in dealt_cards.items() if card == highest_card)

        # Save the dealer to the game
        game.dealer = dealer
        game.save()

        # Calculate player order starting to the left of the dealer
        player_list = list(players)
        dealer_index = player_list.index(dealer)
        player_order = player_list[dealer_index + 1:] + player_list[:dealer_index + 1]

        # Step 3: Reset the deck and deal hands
        deck.extend(dealt_cards.values())  # Return the dealt cards to the deck
        shuffle(deck)

        hands = {}
        for player in players:
            hands[player] = [deck.pop() for _ in range(5)]

        # Prepare the remaining cards for trump selection
        remaining_cards = deck[:4] if len(deck) >= 4 else []

        # Step 4: Prepare the response
        response = {
            "hands": {
                player.name: [f"{card.rank} of {card.suit}" for card in hand]
                for player, hand in hands.items()
            },
            "dealt_cards": {player.name: f"{card.rank} of {card.suit}" for player, card in dealt_cards.items()},
            "dealer": dealer.name,
            "highest_card": f"{highest_card.rank} of {highest_card.suit}",
            "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
            "player_order": [player.name for player in player_order],
        }
        return JsonResponse(response)

    return JsonResponse({"error": "Invalid request method."}, status=400)

@csrf_exempt
def deal_hand(request):
    if request.method == "POST":
        try:
            dealer_name = request.POST.get("dealer")
            dealer = Player.objects.get(name=dealer_name)
            players = Player.objects.all()

            # Shuffle the deck
            deck = list(Card.objects.all())
            shuffle(deck)

            # Use the model's `deal_hand` function to deal cards
            hands, remaining_cards = model_deal_hand(deck, players)

            # Prepare the response
            response = {
                "hands": {
                    player.name: [f"{card.rank} of {card.suit}" for card in hand]
                    for player, hand in hands.items()
                },
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
            }
            return JsonResponse(response)
        except Exception as e:
            print(f"Error in deal_hand: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@csrf_exempt
def pick_trump(request):
    if request.method == "POST":
        try:
            dealer_name = request.POST.get("dealer")
            players = Player.objects.all()

            # Fetch the remaining cards in their current order
            remaining_cards = list(Card.objects.filter(is_trump=False)[:4])  # Fetch 4 cards as a list
            if not remaining_cards:
                raise ValueError("No remaining cards in the deck for trump selection.")

            # Remove the top card for the next round if rejected
            current_card = remaining_cards.pop(0)  # Get and remove the first card
            player_order = list(players)
            dealer = Player.objects.get(name=dealer_name)

            # Rotate the player order to start with the player left of the dealer
            start_index = (player_order.index(dealer) + 1) % len(player_order)
            player_order = player_order[start_index:] + player_order[:start_index]

            # Update the deck
            remaining_cards_queryset = Card.objects.filter(pk__in=[card.pk for card in remaining_cards])
            Card.objects.exclude(pk__in=remaining_cards_queryset).update(is_trump=False)

            # Return the current card and player order for frontend logic
            response = {
                "current_card": f"{current_card.rank} of {current_card.suit}",
                "player_order": [player.name for player in player_order],
            }
            return JsonResponse(response)
        except Exception as e:
            print(f"Error in pick_trump: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@csrf_exempt
def accept_trump(request):
    if request.method == "POST":
        try:
            player_name = request.POST.get("player")
            card_info = request.POST.get("card")
            rank, suit = card_info.split(" of ")
            card = Card.objects.get(rank=rank, suit=suit)
            player = Player.objects.get(name=player_name)

            # Get the player's current hand
            player_hand = PlayedCard.objects.filter(player=player)
            if not player_hand:
                return JsonResponse({"error": f"{player_name} has no cards in their hand."}, status=400)

            # Find the worst card in the player's hand
            def card_rank_value(c):
                rank_order = ['9', '10', 'J', 'Q', 'K', 'A']
                return rank_order.index(c.card.rank)

            worst_card = min(player_hand, key=lambda c: card_rank_value(c))

            # Replace the worst card with the trump card
            worst_card.card.is_trump = False  # Reset old card's trump status
            worst_card.card.save()

            card.is_trump = True
            card.save()
            worst_card.card = card
            worst_card.save()

            # Return the discarded card to the deck
            discarded_card = worst_card.card
            Card.objects.filter(pk=discarded_card.pk).update(is_trump=False)

            # Update the game to reflect the trump suit
            game = Game.objects.latest('id')
            game.trump_suit = suit
            game.save()

            # Prepare the updated hand
            updated_hand = [
                f"{pc.card.rank} of {pc.card.suit}" for pc in PlayedCard.objects.filter(player=player)
            ]

            return JsonResponse({
                "message": f"{player_name} accepted the trump card.",
                "trump_suit": suit,
                "updated_hand": updated_hand
            })

        except Card.DoesNotExist:
            return JsonResponse({"error": "Specified card does not exist."}, status=400)
        except Player.DoesNotExist:
            return JsonResponse({"error": "Specified player does not exist."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)

@csrf_exempt
def reset_game(request):
    if request.method == "POST":
        try:
            # Clear existing game state
            PlayedCard.objects.all().delete()  # Remove all played cards
            Game.objects.all().delete()       # Remove all game data
            Card.objects.all().delete()       # Clear the deck

            # Reinitialize the deck
            for suit, _ in Card.SUITS:
                for rank, _ in Card.RANKS:
                    Card.objects.create(suit=suit, rank=rank)

            return JsonResponse({"message": "Game reset successfully."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)