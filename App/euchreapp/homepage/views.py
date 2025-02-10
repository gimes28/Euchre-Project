from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from random import shuffle
from .models import start_euchre_round, Game, Player, Card, deal_hand as model_deal_hand, PlayedCard, reset_round_state, Hand, GameResult

# Render the homepage
def home(request):
    return render(request, "home.html")  # Reference the template in the root templates directory

# Render the About page
def about(request):
    return render(request, "about.html")

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
        try:
            # Step 1: Clear active game-related data but keep past game records
            PlayedCard.objects.all().delete()  # Remove all played cards from the previous game
            Hand.objects.all().delete()        # Remove all hands from the previous game

            # Step 2: Check for the last game and mark it as completed if unfinished
            last_game = Game.objects.order_by('-id').first()
            if last_game and (last_game.team1_points < 10 or last_game.team2_points < 10):
                GameResult.objects.create(
                    game=last_game,
                    winner=None,  # Prevents NOT NULL constraint failure
                    total_hands=last_game.hands.count(),
                    points={"team1": last_game.team1_points, "team2": last_game.team2_points}
                )

            # Step 3: Create a new game
            game = Game.objects.create()

            # Step 4: Reset the deck (keeping past cards in DB)
            Card.objects.all().update(is_trump=False)  # Reset trump markers, but keep the cards
            deck = list(Card.objects.all())
            shuffle(deck)

            # Step 5: Assign dealer
            players = Player.objects.all()
            if len(deck) < len(players):
                return JsonResponse({"error": "Not enough cards to determine dealer."}, status=400)

            dealt_cards = {player: deck.pop() for player in players}

            # Find the highest card
            def card_rank_value(card):
                rank_order = ['9', '10', 'J', 'Q', 'K', 'A']
                return rank_order.index(card.rank)

            highest_card = max(dealt_cards.values(), key=card_rank_value)
            dealer = next(player for player, card in dealt_cards.items() if card == highest_card)

            # Assign dealer to new game
            game.dealer = dealer
            game.save()

            # Step 6: Calculate player order
            player_list = list(players)
            dealer_index = player_list.index(dealer)
            player_order = player_list[dealer_index + 1:] + player_list[:dealer_index + 1]

            # Step 7: Return cards to deck & shuffle
            deck.extend(dealt_cards.values())
            shuffle(deck)

            # Step 8: Deal hands
            hands = {player: [deck.pop() for _ in range(5)] for player in players}

            # Step 9: Prepare remaining cards for trump selection
            remaining_cards = deck[:4] if len(deck) >= 4 else []

            # Step 10: Send response with initial game data
            response = {
                "hands": {player.name: [f"{card.rank} of {card.suit}" for card in hand] for player, hand in hands.items()},
                "dealt_cards": {player.name: f"{card.rank} of {card.suit}" for player, card in dealt_cards.items()},
                "dealer": dealer.name,
                "highest_card": f"{highest_card.rank} of {highest_card.suit}",
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
                "player_order": [player.name for player in player_order],
                "new_game_id": game.id  # Include new game ID
            }
            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@csrf_exempt
def deal_next_hand(request):
    """
    Handle resetting everything for subsequent rounds, including:
    - Resetting PlayedCard objects
    - Rotating the dealer to the next player
    - Starting the trump suit selection process
    """
    if request.method == "POST":
        try:
            # Retrieve the latest game
            game = Game.objects.latest('id')

            # Reset round state and rotate dealer
            deck = reset_round_state(game)

            # Get all players and cards
            players = Player.objects.all()
            
            # Calculate player order starting to the left of the dealer
            player_list = list(players)
            dealer_index = player_list.index(game.dealer)
            player_order = player_list[dealer_index + 1:] + player_list[:dealer_index + 1]

            # Deal new hands
            hands, remaining_cards = model_deal_hand(deck, players, game)

            # Prepare the response with the updated state
            response = {
                "hands": {
                    player.name: [f"{card.rank} of {card.suit}" for card in hand]
                    for player, hand in hands.items()
                },
                "dealer": game.dealer.name,  # Include the new dealer
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
                "player_order": [player.name for player in player_order],
                "message": "New hands dealt. Begin trump selection."
            }

            return JsonResponse(response)

        except Exception as e:
            print(f"Error in deal_next_hand: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)

@csrf_exempt
def deal_hand(request):
    if request.method == "POST":
        try:
            # Ensure game is initialized or fetch the latest game
            try:
                game = Game.objects.latest('id')
            except Game.DoesNotExist:
                return JsonResponse({"error": "No active game found. Please start a new game first."}, status=400)

            # Shuffle the deck
            deck = list(Card.objects.all())
            shuffle(deck)

            players = Player.objects.all()

            # Calculate player order starting to the left of the dealer
            player_list = list(players)
            dealer_index = player_list.index(game.dealer)
            player_order = player_list[dealer_index + 1:] + player_list[:dealer_index + 1]

            # Deal hands and associate them with the game
            hands, remaining_cards = model_deal_hand(deck, players, game)

            # Prepare the response
            response = {
                "hands": {
                    player.name: [f"{card.rank} of {card.suit}" for card in hand]
                    for player, hand in hands.items()
                },
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
                "dealer": game.dealer.name,  # Include the dealer
                "player_order": [player.name for player in player_order],
                "message": "Hands dealt. Begin trump selection."
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

            if not player_name or not card_info:
                return JsonResponse({"error": "Missing player or card data."}, status=400)

            # Ensure card is in correct format
            try:
                rank, suit = card_info.split(" of ")
            except ValueError:
                return JsonResponse({"error": "Invalid card format."}, status=400)

            # Fetch player and card
            try:
                card = Card.objects.get(rank=rank, suit=suit)
            except Card.DoesNotExist:
                return JsonResponse({"error": f"Card '{card_info}' does not exist."}, status=400)

            try:
                player = Player.objects.get(name=player_name)
            except Player.DoesNotExist:
                return JsonResponse({"error": f"Player '{player_name}' does not exist."}, status=400)

            # Fetch latest game
            try:
                game = Game.objects.latest('id')
            except Game.DoesNotExist:
                return JsonResponse({"error": "No active game found. Please start a game first."}, status=400)

            # Fetch latest hand
            latest_hand = Hand.objects.filter(game=game).order_by('-id').first()
            if not latest_hand:
                return JsonResponse({"error": "No active hand found for the current game."}, status=400)

            # Get player's current hand
            player_hand = PlayedCard.objects.filter(player=player, hand=latest_hand)

            # Ensure player has space for a new card
            if player_hand.count() >= 5:
                # Find lowest non-trump card
                def card_rank_value(c):
                    rank_order = ['9', '10', 'J', 'Q', 'K', 'A']
                    return rank_order.index(c.card.rank)

                non_trump_cards = [pc for pc in player_hand if pc.card.suit != suit]
                worst_card = min(non_trump_cards or player_hand, key=lambda c: card_rank_value(c))

                # Remove the worst card
                print(f"Discarding {worst_card.card.rank} of {worst_card.card.suit} from {player.name}")
                worst_card.delete()

            # Ensure the card is not already in the player's hand
            if PlayedCard.objects.filter(player=player, card=card, hand=latest_hand).exists():
                return JsonResponse({"error": "This card is already in the player's hand."}, status=400)

            # Add the new trump card
            PlayedCard.objects.create(
                player=player,
                card=card,
                hand=latest_hand,
                order=player_hand.count() + 1  # Ensure correct order
            )

            # Update the game's trump suit
            game.trump_suit = suit
            game.save()

            # Retrieve updated hand
            updated_hand = [
                f"{pc.card.rank} of {pc.card.suit}"
                for pc in PlayedCard.objects.filter(player=player, hand=latest_hand)
            ]

            return JsonResponse({
                "message": f"{player_name} accepted the trump card.",
                "trump_suit": suit,
                "updated_hand": updated_hand
            })

        except Exception as e:
            print(f"Error in accept_trump: {str(e)}")
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

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

@csrf_exempt
def start_round(request):
    """
    Handles starting a new round and plays all 5 tricks at once.
    """
    if request.method == "POST":
        try:
            game = Game.objects.latest('id')

            # Ensure a previous hand exists in the game
            if not game.hands.exists():
                return JsonResponse({"error": "No previous round found. Cannot start a new round."}, status=400)

            # Step 1: Retrieve all players
            players = Player.objects.all()
            player_hands = {player: [] for player in players}

            # Step 2: Get the latest hand for the game
            latest_hand = Hand.objects.filter(game=game).order_by('-id').first()
            if not latest_hand:
                return JsonResponse({"error": "No hand found for the current game!"}, status=400)

            # Step 3: Fetch PlayedCards only for this hand and these players
            unplayed_cards = PlayedCard.objects.filter(hand=latest_hand, player__in=players)

            # Debugging output
            print(f"Before starting round, total PlayedCards: {unplayed_cards.count()}")

            # Step 4: Assign cards to player_hands
            for played_card in unplayed_cards:
                player_hands[played_card.player].append(played_card.card)

            # Debugging: Check card assignments
            for player, cards in player_hands.items():
                print(f"{player.name} has {len(cards)} cards AFTER retrieval.")

            # Ensure all players have enough cards before starting the round
            for player in players:
                player_cards = player_hands[player]
                if len(player_cards) < 5:
                    return JsonResponse({"error": f"{player.name} has {len(player_cards)} cards instead of 5!"}, status=500)

            # Step 5: Play the entire round (all 5 tricks)
            round_result = start_euchre_round(game)  # Plays **all 5 tricks**
            
            return round_result  # Returns JSON with full round data

        except Exception as e:
            print(f"Error in start_round: {str(e)}")
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def get_game_score(request):
    """
    Returns the current game score.
    """
    try:
        game = Game.objects.latest('id')
        return JsonResponse({
            "team1": game.team1_points,
            "team2": game.team2_points
        })
    except Game.DoesNotExist:
        return JsonResponse({"error": "No active game found."}, status=400)
    
@csrf_exempt
def get_remaining_cards(request):
    """
    Returns a list of all remaining (unplayed) cards in the current round.
    """
    try:
        game = Game.objects.latest('id')
        latest_hand = Hand.objects.filter(game=game).order_by('-id').first()

        if not latest_hand:
            return JsonResponse({"error": "No active round found."}, status=400)

        # Get all played cards in this round
        played_cards = PlayedCard.objects.filter(hand__game=game).values_list('card', flat=True)

        # Get all cards that haven't been played
        remaining_cards = Card.objects.exclude(id__in=played_cards)

        remaining_cards_list = [f"{card.rank} of {card.suit}" for card in remaining_cards]

        return JsonResponse({"remaining_cards": remaining_cards_list})

    except Exception as e:
        print(f"Error in get_remaining_cards: {str(e)}")
        return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)
    
@csrf_exempt
def play_next_trick(request):
    """
    Plays the next trick and returns its result.
    """
    if request.method == "POST":
        try:
            game = Game.objects.latest('id')

            # Play the next trick
            response = start_euchre_round(game)

            return response  # Returns JSON containing trick details

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


