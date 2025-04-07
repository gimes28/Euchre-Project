from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from random import shuffle
from .models import start_euchre_round, Game, Player, Card, deal_hand as model_deal_hand, PlayedCard, reset_round_state, Hand, GameResult, rotate_dealer, evaluate_trick_winner

import json

from .bot_logic import get_valid_plays  # Adjust based on your structure

def select_bot_card(player, hand, trick_number):
    """
    Determines which card a bot should play during a trick.
    """
    played_cards = list(
        PlayedCard.objects.filter(hand=hand, trick_number=trick_number).order_by('order')
    )

    lead_card = played_cards[0].card if played_cards else None

    valid_cards = get_valid_plays(player, lead_card, hand.trump_suit)

    if not valid_cards:
        raise ValueError(f"No valid cards found for {player.name} to play.")

    return valid_cards[0]  # Simple strategy: play the first valid card


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
    
def parse_card_string(card_str):
    rank, suit = formatCardString(card_str).split(" of ")
    return normalize_card(rank, suit)


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
            kitty = []

            for i, card in enumerate(remaining_cards):
                kitty.append({
                    "rank": card.rank,
                    "suit": card.suit,
                    "faceup": i == 0  # Only the first card is face-up during trump selection
                })


            # Step 8: Send response
            return JsonResponse({
                "hands": {player.name: [f"{card.rank} of {card.suit}" for card in hand] for player, hand in hands.items()},
                "dealt_cards": {player.name: f"{card.rank} of {card.suit}" for player, card in dealt_cards.items()},
                "dealer": dealer.name,
                "highest_card": f"{highest_card.rank} of {highest_card.suit}",
                "remaining_cards": kitty,
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
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=400)

    try:
        # ✅ Parse JSON payload correctly
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)

        trump_round = str(data.get("trump_round"))

        if not trump_round:
            return JsonResponse({"error": "Missing trump round data."}, status=400)

        game = Game.objects.latest("id")
        latest_hand = Hand.objects.filter(game=game).order_by("-id").first()

        if not latest_hand:
            return JsonResponse({"error": "No active hand found for the current game."}, status=400)

        # Round 1: Order up
        if trump_round == "1":
            card_info = data.get("card")
            if not card_info:
                return JsonResponse({"error": "Missing card data."}, status=400)

            if " of " not in card_info:
                return JsonResponse({"error": f"Invalid card format: {card_info}"}, status=400)

            rank, suit = card_info.split(" of ")
            try:
                card = Card.objects.get(rank=rank, suit=suit)
            except Card.DoesNotExist:
                return JsonResponse({"error": f"Card '{card_info}' not found."}, status=400)

            dealer = game.dealer
            dealer_played_cards = PlayedCard.objects.filter(player=dealer, hand=latest_hand)
            dealer_hand = [pc.card for pc in dealer_played_cards]
            dealer_hand.append(card)

            discarded_card = dealer.get_worst_card(dealer_hand, suit)
            dealer_hand.remove(discarded_card)

            dealer_played_cards.delete()

            if dealer.is_human:
                dealer_hand = sort_hand(dealer_hand, suit)

            for i, card in enumerate(dealer_hand):
                PlayedCard.objects.create(
                    player=dealer,
                    card=card,
                    hand=latest_hand,
                    order=i + 1
                )

            # Update human hand (if dealer is not human)
            if not dealer.is_human:
                player = Player.objects.get(is_human=True)
                player_cards = PlayedCard.objects.filter(player=player, hand=latest_hand)
                player_hand = [pc.card for pc in player_cards]
                player_cards.delete()

                sorted_hand = sort_hand(player_hand, suit)
                for i, card in enumerate(sorted_hand):
                    PlayedCard.objects.create(
                        player=player,
                        card=card,
                        hand=latest_hand,
                        order=i + 1
                    )

            updated_hand = [
                f"{pc.card.rank} of {pc.card.suit}"
                for pc in PlayedCard.objects.filter(player=dealer if dealer.is_human else player, hand=latest_hand)
            ]

            game.trump_suit = suit
            game.save()

            return JsonResponse({
                "trump_suit": suit,
                "updated_hand": updated_hand,
                "discarded_card": f"{discarded_card.rank} of {discarded_card.suit}",
                "dealer": dealer.name
            })

        # Round 2: Call a suit
        elif trump_round == "2":
            suit = data.get("suit")
            if not suit:
                return JsonResponse({"error": "Missing suit data."}, status=400)

            player = Player.objects.get(is_human=True)
            player_cards = PlayedCard.objects.filter(player=player, hand=latest_hand)
            player_hand = [pc.card for pc in player_cards]
            player_cards.delete()

            sorted_hand = sort_hand(player_hand, suit)
            for i, card in enumerate(sorted_hand):
                PlayedCard.objects.create(
                    player=player,
                    card=card,
                    hand=latest_hand,
                    order=i + 1
                )

            updated_hand = [
                f"{pc.card.rank} of {pc.card.suit}"
                for pc in PlayedCard.objects.filter(player=player, hand=latest_hand)
            ]

            game.trump_suit = suit
            game.save()

            return JsonResponse({
                "trump_suit": suit,
                "updated_hand": updated_hand
            })

        return JsonResponse({"error": "Invalid trump round."}, status=400)

    except Exception as e:
        return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)


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
    Prepares the round. Does NOT play any tricks automatically.
    Starts the first trick using /play-trick-step/ and human interaction.
    """
    if request.method == "POST":
        try:
            game = Game.objects.latest('id')
            trump_caller_name = request.POST.get("trump_caller")
            trump_caller = Player.objects.get(name=trump_caller_name)
            going_alone = request.POST.get("going_alone") == "true"


            game.going_alone = going_alone
            game.save()

            # Create a new hand for the round
            hand = Hand.objects.create(
                game=game,
                trump_suit=game.trump_suit,
                starting_player=game.dealer.get_next_player(going_alone=going_alone),
                current_trick=1  # This is essential!
            )
            
            # Clear any PlayedCards from the last round
            PlayedCard.objects.filter(hand__game=game).delete()

            print("✅ Round initialized. Waiting for trick logic to start...")

            return JsonResponse({"message": "Round initialized."})

        except Exception as e:
            print("Error in start_round:", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)



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
def get_player_hand(request):
    try:
        game = Game.objects.latest('id')
        hand = Hand.objects.filter(game=game).order_by('-id').first()
        player = Player.objects.get(is_human=True)
        cards = PlayedCard.objects.filter(player=player, hand=hand)
        hand_data = [f"{c.card.rank} of {c.card.suit}" for c in cards]
        return JsonResponse({"hand": hand_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    
# Manual playing card helper functions
def play_card(player, hand, card, player_hands, game):
    """
    Records a card being played by a player during a trick.
    """
    # SAFETY: Don’t play if already played in this trick
    if PlayedCard.objects.filter(hand=hand, player=player, trick_number=hand.current_trick).exists():
        return  # Skip duplicate play

    current_order = PlayedCard.objects.filter(hand=hand, trick_number=hand.current_trick).count() + 1

    PlayedCard.objects.create(
        hand=hand,
        player=player,
        card=card,
        order=current_order,
        trick_number=hand.current_trick
    )

    # Advance if trick is complete
    if PlayedCard.objects.filter(hand=hand, trick_number=hand.current_trick).count() == 4:
        hand.current_trick += 1
        hand.save()

    # Remove from memory hand
    if player in player_hands:
        player_hands[player] = [c for c in player_hands[player] if c != card]


# def evaluate_trick_winner(trump_suit, trick_cards):
#     """
#     Determines the winner of a trick.
#     """
#     lead_card = trick_cards[0].card
#     lead_suit = lead_card.suit
#     best_card = lead_card
#     best_player = trick_cards[0].player

#     for played_card in trick_cards[1:]:
#         challenger = played_card.card
#         if challenger.beats(best_card, lead_suit, trump_suit):
#             best_card = challenger
#             best_player = played_card.player

#     return best_player

    
# Play human card
@csrf_exempt
def play_human_card(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            card_str = data.get("card")
            player_name = data.get("player")

            game = Game.objects.latest('id')
            hand = Hand.objects.filter(game=game).order_by('-id').first()
            player = Player.objects.get(name=player_name)

            # Convert "J of hearts" to actual card
            rank, suit = card_str.split(" of ")
            card = Card.objects.get(rank=rank, suit=suit)

            # Remove card from hand
            player_cards = PlayedCard.objects.filter(player=player, hand=hand)
            player_cards.delete()

            # Rebuild hand without played card
            current_hand_cards = [pc.card for pc in player_cards]
            for i, c in enumerate(current_hand_cards):
                if c != card:
                    PlayedCard.objects.create(player=player, card=c, hand=hand, order=i + 1)

            # Play human card
            trick_cards = list(PlayedCard.objects.filter(hand=hand).order_by("order"))
            play_card(player, hand, card, {player: current_hand_cards}, game)
            trick_cards.append(PlayedCard.objects.get(player=player, hand=hand, card=card))

            # Let bots finish the trick
            while len(trick_cards) < 4:
                players = list(Player.objects.all())
                play_order = players[players.index(hand.starting_player):] + players[:players.index(hand.starting_player)]
                next_player = play_order[len(trick_cards)]
                if next_player.is_human:
                    break
                bot_cards = PlayedCard.objects.filter(hand=hand, player=next_player)
                cards = [pc.card for pc in bot_cards]
                bot_card = next_player.determine_best_card(cards, game.trump_suit, trick_cards)
                play_card(next_player, hand, bot_card, {next_player: cards}, game)
                trick_cards.append(PlayedCard.objects.get(player=next_player, hand=hand, card=bot_card))

            # Evaluate trick winner
            winner = evaluate_trick_winner(game.trump_suit, trick_cards)
            hand.starting_player = winner.name  # winner leads next
            hand.save()

            return JsonResponse({
                "action": "trick_completed",
                "winner": winner.name,
                "cards_played": [
                    {"player": pc.player.name, "card": f"{pc.card.rank} of {pc.card.suit}"}
                    for pc in trick_cards
                ]
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=400)

def evaluate_round_results(hand):
    tricks = PlayedCard.objects.filter(hand=hand)
    trick_counts = {team: 0 for team in ['Player', 'Team Mate', 'Opponent1', 'Opponent2']}
    
    for trick_number in range(5):
        trick_cards = tricks.filter(trick_number=trick_number).order_by('order')
        if len(trick_cards) == 4:
            winner = evaluate_trick_winner(hand.game.trump_suit, trick_cards)
            trick_counts[winner.name] += 1
    
    player_team = trick_counts['Player'] + trick_counts['Team Mate']
    opponent_team = trick_counts['Opponent1'] + trick_counts['Opponent2']

    if player_team > opponent_team:
        hand.winning_team = 'Player Team'
    elif opponent_team > player_team:
        hand.winning_team = 'Opponent Team'
    else:
        hand.winning_team = 'Tie'

    hand.save()

def normalize_card(rank, suit):
    face_map = {'j': 'J', 'q': 'Q', 'k': 'K', 'a': 'A'}
    rank = face_map.get(rank.lower(), rank.capitalize())
    return rank, suit.lower()


def formatCardString(card_str):
    """
    Takes input like 'q_of_spades' or 'Q of Spades' and returns 'Q of spades'.
    """
    if "_of_" in card_str:
        rank, suit = card_str.split("_of_")
    elif " of " in card_str:
        rank, suit = card_str.split(" of ")
    else:
        raise ValueError(f"Invalid card format: {card_str}")
    return f"{rank.upper()} of {suit.lower()}"

def update_game_results(game, team1_tricks, team2_tricks, trump_caller, going_alone):
    """
    Updates the overall game points based on who won the round.
    """
    team1_names = ["Player", "Team Mate"]
    team2_names = ["Opponent1", "Opponent2"]

    if team1_tricks > team2_tricks:
        winning_team = 1
    else:
        winning_team = 2

    # Determine if the caller's team won
    caller_on_winning_team = (
        (winning_team == 1 and trump_caller.name in team1_names) or
        (winning_team == 2 and trump_caller.name in team2_names)
    )

    if going_alone:
        # Alone hand scoring
        if caller_on_winning_team:
            points = 4 if (team1_tricks == 5 or team2_tricks == 5) else 1
        else:
            points = 2  # Euchred
    else:
        # Normal team play scoring
        if caller_on_winning_team:
            points = 2 if (team1_tricks == 5 or team2_tricks == 5) else 1
        else:
            points = 2  # Euchred

    # Apply points
    if winning_team == 1:
        game.team1_points += points
    else:
        game.team2_points += points

    print(f"✅ Round Scoring: Team {winning_team} wins. Caller: {trump_caller.name}, Going Alone: {going_alone}, Points Awarded: {points}")
    game.save()



# Pause trick to allow human play
@csrf_exempt
def play_trick_step(request):
    game = Game.objects.latest('id')
    hand = game.hands.latest('id')
    current_trick = hand.current_trick
    trick_players = Player.turn_order(start=hand.starting_player)
    played_this_trick = PlayedCard.objects.filter(hand=hand, trick_number=current_trick).order_by('order')
    played_players = [pc.player for pc in played_this_trick]

    if request.method == "POST":
        try:
            if not request.body:
                return JsonResponse({"error": "Empty request body."}, status=400)

            data = json.loads(request.body)
            card_str = data.get("card")
            if not card_str:
                return JsonResponse({"error": "No card provided."}, status=400)

            formatted = formatCardString(card_str)
            rank, suit = formatted.split(" of ")
            rank, suit = normalize_card(rank, suit)
            card_obj = Card.objects.get(rank=rank, suit=suit)

            current_player = Player.objects.get(is_human=True)

            if current_player in played_players:
                return JsonResponse({"error": "Player has already played in this trick."}, status=400)

            PlayedCard.objects.create(
                hand=hand,
                player=current_player,
                card=card_obj,
                trick_number=current_trick,
                order=played_this_trick.count()
            )

            played_this_trick = PlayedCard.objects.filter(hand=hand, trick_number=current_trick).order_by('order')

            if len(played_this_trick) == 4:
                winner = evaluate_trick_winner(game.trump_suit, played_this_trick)
                hand.current_trick += 1
                hand.starting_player = winner.name
                hand.save()

                trick_data = {
                    "players": [pc.player.name for pc in played_this_trick],
                    "cards": [str(pc.card) for pc in played_this_trick],
                    "winner": winner.name,
                    "trick_number": current_trick
                }

                if hand.current_trick >= 5:
                    round_results = hand.evaluate_round_results()
                    trump_caller = Player.objects.get(name=hand.starting_player)
                    going_alone = getattr(game, 'going_alone', False)

                    update_game_results(game, round_results["team1_tricks"], round_results["team2_tricks"], trump_caller, going_alone)

                    completed_tricks = []
                    for i in range(1, 6):
                        trick = PlayedCard.objects.filter(hand=hand, trick_number=i).order_by('order')
                        if len(trick) == 4:
                            completed_tricks.append({
                                "trick_number": i,
                                "players": [pc.player.name for pc in trick],
                                "cards": [str(pc.card) for pc in trick],
                                "winner": evaluate_trick_winner(game.trump_suit, trick).name
                            })

                    return JsonResponse({
                        "action": "round_completed",
                        "trick": trick_data,
                        "trick_complete": True,
                        "round_results": {
                            "team1_points": game.team1_points,
                            "team2_points": game.team2_points,
                            "winning_team": round_results["winning_team"]
                        },
                        "tricks": completed_tricks  # now an array of all 5 tricks
                    })

                return JsonResponse({
                    "action": "trick_completed",
                    "trick": trick_data,
                    "trick_complete": True
                })

            return JsonResponse({
                "message": "Card played.",
                "trick": {
                    "players": [pc.player.name for pc in played_this_trick],
                    "cards": [str(pc.card) for pc in played_this_trick],
                    "trick_number": current_trick
                },
                "trick_complete": False
            })

        except Exception as e:
            import traceback
            print("🔥 Exception in play_trick_step:", traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "GET":
        remaining_players = [p for p in trick_players if p not in played_players]

        if not remaining_players:
            return JsonResponse({"error": "Trick already complete."}, status=400)

        current_player = remaining_players[0]

        if current_player.is_human:
            return JsonResponse({
                "action": "awaiting_player",
                "played_so_far": [
                    {"player": pc.player.name, "card": str(pc.card)} for pc in played_this_trick
                ],
                "trick_number": current_trick
            })

        # Bot logic
        card_to_play = select_bot_card(current_player, hand, current_trick)
        PlayedCard.objects.create(
            hand=hand,
            player=current_player,
            card=card_to_play,
            trick_number=current_trick,
            order=played_this_trick.count()
        )

        played_this_trick = PlayedCard.objects.filter(hand=hand, trick_number=current_trick).order_by('order')

        if len(played_this_trick) == 4:
            winner = evaluate_trick_winner(game.trump_suit, played_this_trick)
            hand.current_trick += 1
            hand.starting_player = winner.name
            hand.save()

            trick_data = {
                "players": [pc.player.name for pc in played_this_trick],
                "cards": [str(pc.card) for pc in played_this_trick],
                "winner": winner.name,
                "trick_number": current_trick
            }

            if hand.current_trick >= 5:
                round_results = hand.evaluate_round_results()
                trump_caller = Player.objects.get(name=hand.starting_player)
                going_alone = getattr(game, 'going_alone', False)

                update_game_results(game, round_results["team1_tricks"], round_results["team2_tricks"], trump_caller, going_alone)

                completed_tricks = []
                for i in range(1, 6):
                    trick = PlayedCard.objects.filter(hand=hand, trick_number=i).order_by('order')
                    if len(trick) == 4:
                        completed_tricks.append({
                            "trick_number": i,
                            "players": [pc.player.name for pc in trick],
                            "cards": [str(pc.card) for pc in trick],
                            "winner": evaluate_trick_winner(game.trump_suit, trick).name
                        })

                return JsonResponse({
                    "action": "round_completed",
                    "trick": trick_data,
                    "trick_complete": True,
                    "round_results": {
                        "team1_points": game.team1_points,
                        "team2_points": game.team2_points,
                        "winning_team": round_results["winning_team"]
                    },
                    "tricks": completed_tricks
                })

            return JsonResponse({
                "action": "trick_completed",
                "trick": trick_data,
                "trick_complete": True
            })

    if 'current_player' in locals() and 'card_to_play' in locals():
        return JsonResponse({
            "action": "bot_played",
            "player": current_player.name,
            "card": str(card_to_play),
            "trick_complete": PlayedCard.objects.filter(hand=hand, trick_number=current_trick).count() == 4
        })

    return JsonResponse({"error": "Invalid request method."}, status=405)


# Reset trick
@csrf_exempt
def end_trick(request):
    try:
        game = Game.objects.latest("id")
        hand = Hand.objects.filter(game=game).order_by("-id").first()

        # Only clear current trick
        PlayedCard.objects.filter(hand=hand, trick_number=hand.current_trick).delete()

        # Advance to next trick
        hand.current_trick += 1
        hand.save()

        return JsonResponse({"message": "Trick reset."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    
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
    
    
