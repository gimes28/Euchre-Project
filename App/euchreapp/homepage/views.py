from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from random import shuffle
from .models import start_euchre_round, Game, Player, Card, deal_hand as model_deal_hand, PlayedCard, reset_round_state, Hand, GameResult, rotate_dealer
import json

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
            print("🔥 Starting a new game while keeping previous data...")

            # Step 1: Mark the last game as completed if unfinished
            last_game = Game.objects.order_by('-id').first()
            if last_game and not GameResult.objects.filter(game=last_game).exists():
                GameResult.objects.create(
                    game=last_game,
                    winner=None,  
                    total_hands=last_game.hands.count(),
                    points={"team1": last_game.team1_points, "team2": last_game.team2_points},
                )
                print(f"✅ Archived last game: {last_game.id}")

            # Step 2: Create a new game
            game = Game.objects.create()

            # Step 3: Reset only the deck for this game
            print("♠️ Creating a fresh deck for the new game...")
            suits = ["hearts", "diamonds", "clubs", "spades"]
            ranks = ["9", "10", "J", "Q", "K", "A"]

            # Only create cards that are not already in the database
            existing_cards = {(card.rank, card.suit) for card in Card.objects.all()}
            new_cards = []

            for suit in suits:
                for rank in ranks:
                    if (rank, suit) not in existing_cards:
                        new_cards.append(Card(suit=suit, rank=rank, is_trump=False))

            # Bulk create to speed up performance
            Card.objects.bulk_create(new_cards)
            print(f"✅ {len(new_cards)} new cards created for the game.")

            # Step 4: Shuffle and assign dealer
            deck = list(Card.objects.all())
            shuffle(deck)

            players = Player.objects.all()
            if len(deck) < len(players):
                return JsonResponse({"error": "Not enough cards to determine dealer."}, status=400)

            dealt_cards = {player: deck.pop() for player in players}

            if not dealt_cards:
                return JsonResponse({"error": "No cards were dealt. Check deck integrity."}, status=500)
            try:
                highest_card = max(dealt_cards.values(), key=lambda card: ["9", "10", "J", "Q", "K", "A"].index(card.rank))
            except ValueError:
                return JsonResponse({"error": "Invalid card data while selecting highest card."}, status=500)

            dealer = next(player for player, card in dealt_cards.items() if card == highest_card)

            game.dealer = dealer
            game.save()

            # Step 5: Return cards to deck & shuffle
            deck.extend(dealt_cards.values())
            shuffle(deck)

            # Step 6: Deal hands
            hands = {player: [deck.pop() for _ in range(5)] for player in players}

            # Step 7: Prepare remaining cards for trump selection
            remaining_cards = deck[:4] if len(deck) >= 4 else []

            # Step 8: Send response
            return JsonResponse({
                "hands": {player.name: [f"{card.rank} of {card.suit}" for card in hand] for player, hand in hands.items()},
                "dealt_cards": {player.name: f"{card.rank} of {card.suit}" for player, card in dealt_cards.items()},
                "dealer": dealer.name,
                "highest_card": f"{highest_card.rank} of {highest_card.suit}",
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
                "player_order": [player.name for player in players],
                "new_game_id": game.id
            })

        except Exception as e:
            print(f"🚨 ERROR in start_new_game: {str(e)}")
            return JsonResponse({"error": f"🔥 ERROR in start_new_game: {str(e)}"}, status=500)

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

            # Reset round state (This already rotates the dealer)
            deck = reset_round_state(game)

            # ✅ Remove extra dealer rotation
            # The dealer should already be rotated inside `reset_round_state`
            new_dealer = game.dealer

            print(f"✅ New dealer assigned: {new_dealer.name}")

            # Get all players and cards
            players = Player.objects.all()
            
            # Calculate player order starting to the left of the new dealer
            player_list = list(players)
            dealer_index = player_list.index(new_dealer)
            player_order = player_list[dealer_index + 1:] + player_list[:dealer_index + 1]

            # Deal new hands
            hands, remaining_cards = model_deal_hand(deck, players, game)

             # Sort the hands
            for player, cards in hands.items():
                if player.is_human:
                    sorted_cards = sort_hand(cards)
                    hands[player] = sorted_cards

            # Prepare the response with the updated state
            response = {
                "hands": {
                    player.name: [f"{card.rank} of {card.suit}" for card in hand]
                    for player, hand in hands.items()
                },
                "dealer": new_dealer.name.strip(),  # Removes any extra spaces
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
                "player_order": [{"name": player.name, "is_human": player.is_human} for player in player_order],
                "message": f"New hands dealt. {new_dealer.name} is now the dealer. Begin trump selection."
            }

            return JsonResponse(response)

        except Exception as e:
            print(f"🚨 Error in deal_next_hand: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)




@csrf_exempt
def deal_hand(request):
    if request.method == "POST":
        try:
            print("📢 deal_hand() function was called!")

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

            # Debugging: Print deck and player information
            print(f"🔥 DEBUG: Deck contains {len(deck)} cards before dealing.")
            print(f"🔥 DEBUG: Players in game: {[player.name for player in players]}")

            # **Call `model_deal_hand()` and log its output**
            result = model_deal_hand(deck, players, game)

            # If `model_deal_hand()` doesn't return a tuple, fix it
            if not isinstance(result, tuple) or len(result) != 2:
                print(f"🚨 ERROR: Unexpected return value from model_deal_hand(): {result}")
                return JsonResponse({"error": "Unexpected return value from deal_hand(). Check function implementation."}, status=500)

            hands, remaining_cards = result  # This line previously failed

            # Sort the hands
            for player, cards in hands.items():
                if player.is_human:
                    sorted_cards = sort_hand(cards)
                    hands[player] = sorted_cards

            # Prepare the response
            response = {
                "hands": {
                    player.name: [f"{card.rank} of {card.suit}" for card in hand]
                    for player, hand in hands.items()
                },
                "remaining_cards": [f"{card.rank} of {card.suit}" for card in remaining_cards],
                "dealer": game.dealer.name,  # Include the dealer
                "player_order": [{"name": player.name, "is_human": player.is_human} for player in player_order],
                "message": "Hands dealt. Begin trump selection."
            }

            return JsonResponse(response)

        except Exception as e:
            print(f"🚨 ERROR in deal_hand(): {str(e)}")
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

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
            trump_round = request.POST.get("trump_round")

            if not trump_round:
                return JsonResponse({"error": "Missing trump round data."}, status=400)

            # Fetch latest game
            try:
                game = Game.objects.latest('id')
            except Game.DoesNotExist:
                return JsonResponse({"error": "No active game found. Please start a game first."}, status=400)

            # Fetch latest hand
            latest_hand = Hand.objects.filter(game=game).order_by('-id').first()
            if not latest_hand:
                return JsonResponse({"error": "No active hand found for the current game."}, status=400)

            # Handle round 1 of trump selection
            if trump_round == "1":
                card_info = request.POST.get("card")
                if not card_info:
                    return JsonResponse({"error": "Missing card data."}, status=400)

                # Ensure card is in correct format
                if " of " not in card_info:
                    return JsonResponse({"error": f"Invalid card format: '{card_info}'"}, status=400)

                try:
                    rank, suit = card_info.split(" of ")
                except ValueError:
                    return JsonResponse({"error": f"Card parsing error: '{card_info}'"}, status=400)
                
                # Fetch card
                try:
                    card = Card.objects.get(rank=rank, suit=suit)
                except Card.DoesNotExist:
                    return JsonResponse({"error": f"Card '{card_info}' does not exist."}, status=400)

                # Get player's current hand
                dealer_played_cards = PlayedCard.objects.filter(player=game.dealer, hand=latest_hand)

                # Convert to list of Cards for dealer_pickup
                dealer_hand = [played_card.card for played_card in dealer_played_cards]

                dealer_hand.append(card)
                
                # updated_dealer_hand = game.dealer.dealer_pickup(dealer_hand, card)
                discarded_card = game.dealer.get_worst_card(dealer_hand, card.suit)
                dealer_hand.remove(discarded_card)

                dealer_played_cards.delete()

                if game.dealer.is_human:
                    dealer_hand = sort_hand(dealer_hand, suit)

                for i, card in enumerate(dealer_hand):
                    PlayedCard.objects.create(
                        player=game.dealer,
                        card=card,
                        hand=latest_hand,
                        order=i + 1  # Ensure correct order
                    )

                if not game.dealer.is_human:
                    player = Player.objects.get(is_human=True)
                    player_cards = PlayedCard.objects.filter(player=player, hand=latest_hand)
                    player_hand = [played_card.card for played_card in player_cards]
                    sorted_player_hand = sort_hand(player_hand, suit)

                    player_cards.delete()

                    for i, card in enumerate(sorted_player_hand):
                        PlayedCard.objects.create(
                            player=player,
                            card=card,
                            hand=latest_hand,
                            order=i + 1
                        )

                # Retrieve updated hand
                if game.dealer.is_human:
                    updated_hand = [
                        f"{pc.card.rank} of {pc.card.suit}"
                        for pc in PlayedCard.objects.filter(player=game.dealer, hand=latest_hand)
                    ]
                else:
                    updated_hand = [
                        f"{pc.card.rank} of {pc.card.suit}"
                        for pc in PlayedCard.objects.filter(player=player, hand=latest_hand)
                    ]
                print(f"Updated hand: {updated_hand}")

                # Update the game's trump suit
                game.trump_suit = suit
                game.save()

                return JsonResponse({
                    "trump_suit": suit,
                    "updated_hand": updated_hand,
                    "discarded_card": f"{discarded_card.rank} of {discarded_card.suit}",
                    "dealer": game.dealer.name
                })

            # Handle round 2 of trump selection
            elif trump_round == "2":
                suit = request.POST.get("suit")
                if not suit:
                    return JsonResponse({"error": "Missing suit data."}, status=400)
                
                player = Player.objects.get(is_human=True)
                player_cards = PlayedCard.objects.filter(player=player, hand=latest_hand)
                player_hand = [played_card.card for played_card in player_cards]
                sorted_player_hand = sort_hand(player_hand, suit)

                player_cards.delete()

                for i, card in enumerate(sorted_player_hand):
                    PlayedCard.objects.create(
                        player=player,
                        card=card,
                        hand=latest_hand,
                        order=i + 1
                    )

                # Retrieve updated hand
                updated_hand = [
                    f"{pc.card.rank} of {pc.card.suit}"
                    for pc in PlayedCard.objects.filter(player=player, hand=latest_hand)
                ]
                print(f"Updated hand: {updated_hand}")

                # Update the game's trump suit
                game.trump_suit = suit
                game.save()
                
                return JsonResponse({
                    "trump_suit": suit,
                    "updated_hand": updated_hand
                })
            
            return JsonResponse({"error": "Invalid trump round."}, status=400)

        except Exception as e:
            print(f"Error in accept_trump: {str(e)}")
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)



@csrf_exempt
def reset_game(request):
    if request.method == "POST":
        try:
            # Archive past games instead of deleting them
            for game in Game.objects.all():
                if not GameResult.objects.filter(game=game).exists():
                    GameResult.objects.create(
                        game=game,
                        winner=None,  # If game was unfinished, set winner as None
                        total_hands=game.hands.count(),
                        points={"team1": game.team1_points, "team2": game.team2_points}
                    )

            # Clear played cards and active hands
            PlayedCard.objects.all().delete()  
            Hand.objects.all().delete()        

            # Reset ongoing games (instead of deleting, clear fields)
            Game.objects.all().update(dealer=None, trump_suit="", team1_points=0, team2_points=0)

            # 🔥 Ensure the deck is fully recreated
            Card.objects.all().delete()  # Ensure no duplicate cards remain

            # Create a fresh deck of unique cards
            for suit, _ in Card.SUITS:
                for rank, _ in Card.RANKS:
                    Card.objects.create(suit=suit, rank=rank, is_trump=False)

            return JsonResponse({"message": "Game reset successfully and archived."})

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)



@csrf_exempt
def start_round(request):
    """
    Handles starting a new round and plays all 5 tricks at once.
    """
    if request.method == "POST":
        try:
            game = Game.objects.latest('id')
            trump_caller_name = request.POST.get("trump_caller")
            going_alone = request.POST.get("going_alone") == "true"

            try:
                trump_caller = Player.objects.get(name=trump_caller_name)
            except Player.DoesNotExist:
                return JsonResponse({"error": f"Player '{trump_caller_name}' does not exist."}, status=400)

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
            round_result = start_euchre_round(game, trump_caller, going_alone)  # Plays **all 5 tricks**
            
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

        # Get all cards that haven't been played, excluding the Player's hand
        player = Player.objects.get(name="Player")  # Adjust if Player's name differs
        player_hand = PlayedCard.objects.filter(player=player, hand=latest_hand).values_list('card', flat=True)

        remaining_cards = Card.objects.exclude(id__in=played_cards).exclude(id__in=player_hand)

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

@csrf_exempt
def determine_bot_trump_decision(request):
    if request.method == "POST":
        try:
            # Fetch the latest game
            game = Game.objects.latest('id')

            # Fetch the player
            bot_name = request.POST.get("player")

            # Fetch the trump round
            trump_round = request.POST.get("trump_round")

            try:
                bot = Player.objects.get(name=bot_name)
            except Player.DoesNotExist:
                return JsonResponse({"error": f"Player '{bot_name}' does not exist."}, status=400)
            
            # Fetch the latest hand
            latest_hand = Hand.objects.filter(game=game).order_by('-id').first()

            bot_hand_played_cards = PlayedCard.objects.filter(player=bot, hand=latest_hand)
            bot_hand = [played_card.card for played_card in bot_hand_played_cards]

            # Fetch the up card
            up_card_string = request.POST.get("up_card")
            up_card_rank, up_card_suit = up_card_string.split(" of ")
            up_card = Card.objects.get(rank=up_card_rank, suit=up_card_suit)

            # Fetch the player order
            player_order_data = json.loads(request.POST.get("player_order"))
            player_order = [Player.objects.get(name=player['name']) for player in player_order_data]

            # Determine the trump decision
            trump_decision, going_alone = bot.determine_trump(bot_hand, game.dealer, up_card, player_order, trump_round)

            return JsonResponse({"decision": trump_decision, "going_alone": going_alone})

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)
        
def sort_hand(hand, trump_suit=None):
    """
    Sorts a list of Cards based on their suits and ranks
    """
    def euchre_sort_key(card):
        suit_order = {'hearts': 0, 'diamonds': 1, 'clubs': 2, 'spades': 3}

        if trump_suit:
            if card.is_right_bower(trump_suit):
                suit_group = 0
            elif card.is_left_bower(trump_suit):
                suit_group = 1
            elif card.suit == trump_suit:
                suit_group = 2
            else:
                suit_group = suit_order.get(card.suit, 4) + 3
        else:
            suit_group = suit_order.get(card.suit, 4)
        
        rank_values = {
            'A': 6,
            'K': 5,
            'Q': 4,
            'J': 3,
            '10': 2,
            '9': 1
        }

        return (suit_group, -rank_values.get(card.rank, 0))
            
    print(f"Sorting hand")
    return sorted(hand, key=euchre_sort_key)
    
    
