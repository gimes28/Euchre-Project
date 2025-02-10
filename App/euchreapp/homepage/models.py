from django.db import models
from django.db.models import Max
from random import shuffle
from django.http import JsonResponse
import time


# Create your models here.
# These will automatically create a database model to use the built in sqlite3

class Player(models.Model):
    name = models.CharField(max_length=100)
    is_human = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Game(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dealer = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='games_as_dealer')
    trump_suit = models.CharField(max_length=10, choices=[('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')])
    team1_points = models.IntegerField(default=0)  # Points for Human + Bot2
    team2_points = models.IntegerField(default=0)  # Points for Bot1 + Bot3

    def __str__(self):
        return f"Game {self.id} started at {self.created_at}"


class Hand(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='hands')
    dealer = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='dealt_hands')
    trump_suit = models.CharField(max_length=10, choices=[('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')])
    winner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='won_hands', null=True, blank=True)

    def __str__(self):
        return f"Hand {self.id} of Game {self.game.id}"


class Card(models.Model):
    SUITS = [('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')]
    RANKS = [
        ('9', '9'), ('10', '10'), ('J', 'Jack'), ('Q', 'Queen'),
        ('K', 'King'), ('A', 'Ace')
    ]

    suit = models.CharField(max_length=10, choices=SUITS)
    rank = models.CharField(max_length=5, choices=RANKS)
    is_trump = models.BooleanField(default=False)

    class Meta:
        unique_together = ('suit', 'rank')  # Prevent duplicates

    def __str__(self):
        return f"{self.rank} of {self.suit}" + (" (Trump)" if self.is_trump else "")


class PlayedCard(models.Model):
    hand = models.ForeignKey(Hand, on_delete=models.CASCADE, related_name='played_cards', null=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    order = models.IntegerField()

    class Meta:
        unique_together = ('player', 'card')

    def __str__(self):
        return f"{self.player.name} played {self.card}"


class GameResult(models.Model):
    game = models.OneToOneField(Game, on_delete=models.CASCADE)
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')  # Allow NULL values
    total_hands = models.IntegerField()
    points = models.JSONField()  # Example: {"team1": 10, "team2": 8}

    def __str__(self):
        return f"Result of Game {self.game.id}"
    
    
# Helper functions to make the game work correctly

def initialize_game(players):
    """
    Initializes the game and returns a shuffled deck of cards.
    """
    # Clear existing cards to ensure no duplicates
    Card.objects.all().delete()

    # Create a full deck of unique cards
    deck = []
    for suit, _ in Card.SUITS:
        for rank, _ in Card.RANKS:
            card = Card.objects.create(suit=suit, rank=rank)
            deck.append(card)
    shuffle(deck)

    # Create the game
    game = Game.objects.create()

    # Create players (avoid duplicates)
    for player in players:
        Player.objects.get_or_create(name=player["name"], is_human=player["is_human"])

    return game, deck


# def deal_cards(deck, players):
#     """
#     Deals 5 cards to each player and updates the database.
#     """
#     hands = {player: [] for player in players}
#     for _ in range(5):
#         for player in players:
#             card = deck.pop()
#             hands[player].append(card)
#             # Assign card to the player in the database if necessary
#             # Example: Assign cards to a `PlayerCard` model
#     return hands

def deal_hand(deck, players, game):
    """
    Deals a hand of 5 cards to each player and creates PlayedCard objects.
    """
    if not game:
        raise ValueError("No game provided. Please start a new game.")

    if not deck or len(deck) < len(players) * 5:
        raise ValueError("Not enough cards in the deck to deal a full hand.")

    # Clear PlayedCard objects only if it's a new round
    PlayedCard.objects.filter(hand__game=game).delete()

    # Create a new Hand for this round
    hand = Hand.objects.create(
        game=game,
        dealer=game.dealer,
        trump_suit=game.trump_suit
    )

    # 🔥 Debug: Check deck size before dealing
    print(f"DEBUG: Deck size before dealing: {len(deck)}")

    # Initialize hands for each player
    hands = {player: [] for player in players}

    # Deal cards to each player
    for player in players:
        for _ in range(5):
            if deck:
                card = deck.pop()

                # 🔥 Ensure the card is not already assigned to another player
                existing_entry = PlayedCard.objects.filter(player=player, card=card).exists()
                if existing_entry:
                    raise ValueError(f"🔥 ERROR: Duplicate card detected: {card.rank} of {card.suit} for {player.name}!")

                hands[player].append(card)

                # Save played card in database
                PlayedCard.objects.create(
                    player=player,
                    card=card,
                    hand=hand,
                    order=len(hands[player])
                )
            else:
                raise ValueError(f"🔥 ERROR: Not enough cards left in deck to deal a full hand!")

    # 🔥 Debug: Check each player's hand size
    for player, hand in hands.items():
        print(f"DEBUG: {player.name} was dealt {len(hand)} cards.")

    return hands, deck



def assign_trump(deck, trump_suit):
    """
    Marks cards in the deck as trump cards based on the trump suit.
    """
    for card in deck:
        card.is_trump = card.suit == trump_suit
        card.save()
    

def determine_best_card(hand, trump_suit, played_cards):
    """
    Determines the best card to play based on Euchre rules.
    """
    if not hand:
        raise ValueError("Hand is empty, no card can be played.")

    lead_suit = played_cards[0].card.suit if played_cards else None
    left_bower_suit = "clubs" if trump_suit == "spades" else \
                      "spades" if trump_suit == "clubs" else \
                      "diamonds" if trump_suit == "hearts" else "hearts"

    trump_cards = []
    lead_suit_cards = []
    other_cards = []

    for card in hand:
        if card.suit == trump_suit or (card.suit == left_bower_suit and card.rank == "J"):
            trump_cards.append(card)
        elif card.suit == lead_suit:
            lead_suit_cards.append(card)
        else:
            other_cards.append(card)

    def euchre_rank(card):
        """Assign rank based on Euchre rules."""
        if card.rank == "J":
            if card.suit == trump_suit:
                return 20  # Right Bower (Highest)
            elif card.suit == left_bower_suit:
                return 19  # Left Bower
        if card.suit == trump_suit:
            return 10 + ["9", "10", "Q", "K", "A"].index(card.rank)
        if card.suit == lead_suit:
            return 5 + ["9", "10", "J", "Q", "K", "A"].index(card.rank)
        return ["9", "10", "J", "Q", "K", "A"].index(card.rank)

    # Follow suit if possible
    if lead_suit_cards:
        return max(lead_suit_cards, key=euchre_rank)

    # Otherwise, play the best trump if available
    if trump_cards:
        return max(trump_cards, key=euchre_rank)

    # Otherwise, play the lowest non-trump card
    return min(other_cards, key=euchre_rank)



    
# def evaluate_trick_winner(trump_suit, played_cards):
#     """
#     Determines the winner of the current trick based on Euchre rules.
    
#     Args:
#         trump_suit (str): The trump suit for the current hand.
#         played_cards (QuerySet): The cards that have been played in the trick.

#     Returns:
#         Player: The player who won the trick.
#     """
#     if not played_cards:
#         return None

#     # Determine the lead suit (first card played)
#     lead_suit = played_cards[0].card.suit if played_cards else None

#     # Determine the Left Bower suit (same color as trump)
#     left_bower_suit = "clubs" if trump_suit == "spades" else \
#                       "spades" if trump_suit == "clubs" else \
#                       "diamonds" if trump_suit == "hearts" else "hearts"

#     # Helper function to determine Euchre rank value
#     def euchre_rank(card):
#         """ Assigns rank values based on Euchre hierarchy. """
#         if card.rank == "J":
#             if card.suit == trump_suit:
#                 return 20  # Right Bower (Highest)
#             elif card.suit == left_bower_suit:
#                 return 19  # Left Bower (2nd Highest)
#         if card.suit == trump_suit:
#             return 10 + ["9", "10", "Q", "K", "A"].index(card.rank)  # Higher value for trump
#         if card.suit == lead_suit:
#             return 5 + ["9", "10", "J", "Q", "K", "A"].index(card.rank)  # Next priority: lead suit
#         return ["9", "10", "J", "Q", "K", "A"].index(card.rank)  # Lowest priority: off-suit

#     # Determine the highest-ranked card
#     winning_card = max(played_cards, key=lambda pc: euchre_rank(pc.card))

#     # Return the player who played the winning card
#     return winning_card.player

def evaluate_trick_winner(trump_suit, played_cards):
    """
    Determines the winner of the current trick based on Euchre rules.
    """
    if not played_cards:
        return None

    lead_suit = played_cards[0].card.suit
    left_bower_suit = "clubs" if trump_suit == "spades" else \
                      "spades" if trump_suit == "clubs" else \
                      "diamonds" if trump_suit == "hearts" else "hearts"

    def euchre_rank(card):
        """ Assigns rank values based on Euchre hierarchy. """
        if card.rank == "J":
            if card.suit == trump_suit:
                return 20  # Right Bower (Highest)
            elif card.suit == left_bower_suit:
                return 19  # Left Bower
        if card.suit == trump_suit:
            return 10 + ["9", "10", "Q", "K", "A"].index(card.rank)
        if card.suit == lead_suit:
            return 5 + ["9", "10", "J", "Q", "K", "A"].index(card.rank)
        return ["9", "10", "J", "Q", "K", "A"].index(card.rank)

    # Find the highest-ranked card
    winning_card = max(played_cards, key=lambda pc: euchre_rank(pc.card))
    return winning_card.player



# def update_game_results(game):
#     """
#     Updates the game results based on hands played.
#     Assigns points to the winning team and checks if a team has reached 10 points.
#     """
#     results = {"team1": 0, "team2": 0}

#     # Calculate the number of hands won by each team
#     for hand in game.hands.all():
#         winning_player = hand.winner
#         if winning_player:
#             if winning_player.name in ["Human", "Bot2"]:  # Team 1: Human + Bot2
#                 results["team1"] += 1
#             else:  # Team 2: Bot1 + Bot3
#                 results["team2"] += 1

#     # Assign points based on hands won in the round
#     if results["team1"] >= 3:
#         if results["team1"] == 5:
#             game.team1_points += 2  # Team 1 wins all hands
#         else:
#             game.team1_points += 1  # Team 1 wins 3 or more hands
#     if results["team2"] >= 3:
#         if results["team2"] == 5:
#             game.team2_points += 2  # Team 2 wins all hands
#         else:
#             game.team2_points += 1  # Team 2 wins 3 or more hands

#     game.save()

#     # Check if a team has reached 10 points
#     if game.team1_points >= 10 or game.team2_points >= 10:
#         # Check if a GameResult already exists
#         if not GameResult.objects.filter(game=game).exists():
#             # Determine the winning team
#             winner = None
#             if game.team1_points >= 10:
#                 winner = Player.objects.filter(name="Human").first()  # Human's team wins
#             else:
#                 winner = Player.objects.filter(name__in=["Bot1", "Bot3"]).first()  # Bot's team wins

#             # Create GameResult for the game
#             GameResult.objects.create(
#                 game=game,
#                 winner=winner,
#                 total_hands=game.hands.count(),
#                 points={"team1": game.team1_points, "team2": game.team2_points},
#             )

#         print(f"Game over! Winner: {'Team 1' if game.team1_points >= 10 else 'Team 2'}")

def update_game_results(game, team1_tricks, team2_tricks):
    """
    Updates game results after each round based on tricks won.
    """
    if team1_tricks >= 3:
        game.team1_points += 1 if team1_tricks < 5 else 2  # ✅ CORRECTED to game.team1_points
    if team2_tricks >= 3:
        game.team2_points += 1 if team2_tricks < 5 else 2  # ✅ CORRECTED to game.team2_points

    game.save()

    # Check for game-winning condition
    if game.team1_points >= 10 or game.team2_points >= 10:
        winner = "Team 1" if game.team1_points >= 10 else "Team 2"

        GameResult.objects.create(
            game=game,
            winner=Player.objects.filter(name="Player").first() if game.team1_points >= 10 else Player.objects.filter(name__in=["Opponent1", "Opponent2"]).first(),
            total_hands=game.hands.count(),
            points={"team1": game.team1_points, "team2": game.team2_points},
        )
        print(f"Game over! Winner: {winner}")



        
def reset_round_state(game):
    """
    Resets the round-specific state, including clearing PlayedCard entries
    and preparing for a new round with dealer rotation.
    """
    # Clear PlayedCard objects
    PlayedCard.objects.filter(hand__game=game).delete()

    # Rotate dealer
    game.dealer = rotate_dealer(game)
    game.save()

    # Shuffle a new deck
    deck = list(Card.objects.all())
    shuffle(deck)  # Ensures cards are shuffled properly before dealing

    return deck


def rotate_dealer(game):
    """
    Rotates the dealer to the player on the left of the current dealer.
    """
    players = list(Player.objects.all())
    if not game.dealer:
        return players[0]  # Default to the first player if no dealer is set

    dealer_index = players.index(game.dealer)
    next_dealer_index = (dealer_index + 1) % len(players)
    return players[next_dealer_index]

def play_card(player, hand, card, player_hands, game):
    """
    Plays a card for a player, removing it from their hand and adding it to the PlayedCard model.

    Args:
        player (Player): The player who is playing the card.
        hand (Hand): The current hand being played.
        card (Card): The card to play.
        player_hands (dict): A dictionary mapping players to their current hands.

    Raises:
        ValueError: If the card is not in the player's hand.
    """
    if card is None:
        raise ValueError(f"Invalid card provided for player {player.name}.")

    if card not in player_hands[player]:
        raise ValueError(f"{card} is not in {player.name}'s hand.")

    # Set the trump suit if it hasn't been chosen yet
    if game.trump_suit is None:
        game.trump_suit = card.suit
        game.save()
        print(f"Trump suit has been set to {game.trump_suit} based on {player.name}'s first card.")

    # Delete any existing PlayedCard entry for this player-card combination
    PlayedCard.objects.filter(player=player, card=card).delete()

    # Create a new PlayedCard entry for the current hand
    PlayedCard.objects.create(
        hand=hand,
        player=player,
        card=card,
        order=len(hand.played_cards.all()) + 1  # Set the correct play order
    )

    # Remove the card from the player's hand
    player_hands[player].remove(card)

    

# def play_card(player, hand, card, player_hands, game):
#     """
#     Plays a card for a player, removing it from their hand and adding it to the PlayedCard model.

#     Args:
#         player (Player): The player who is playing the card.
#         hand (Hand): The current hand being played.
#         card (Card): The card to play.
#         player_hands (dict): A dictionary mapping players to their current hands.

#     Raises:
#         ValueError: If the card is not in the player's hand.
#     """
    
#     if player.is_human:
#         print(f"{player.name}, choose a card to play from: {[str(c) for c in player_hands[player]]}")
#         return  # Wait for user input via frontend
    
#     # Ensure the card is in the player's hand
#     if card is None:
#         raise ValueError(f"Invalid card provided for player {player.name}.")

#     if card not in player_hands[player]:
#         raise ValueError(f"{card} is not in {player.name}'s hand.")

#     # Delete any existing PlayedCard entry for this player-card combination
#     PlayedCard.objects.filter(player=player, card=card).delete()

#     # Create a new PlayedCard entry for the current hand
#     PlayedCard.objects.create(
#         hand=hand,
#         player=player,
#         card=card,
#         order=len(hand.played_cards.all()) + 1  # Set the correct play order
#     )
    
#     # If trump_suit is not set, establish it with the first played card
#     if game.trump_suit is None:
#         game.trump_suit = card.suit
#         game.save()
#         # Notify players of the newly established trump suit
#         notify_players(f"The trump suit has been set to {game.trump_suit} based on the first card played.")

#     # Remove the card from the player's hand
#     player_hands[player].remove(card)

def update_remaining_cards_frontend():
    """
    Triggers an update to the frontend for remaining cards.
    """
    try:
        game = Game.objects.latest('id')
        latest_hand = Hand.objects.filter(game=game).order_by('-id').first()

        if not latest_hand:
            return

        # Get all played cards
        played_cards = PlayedCard.objects.filter(hand__game=game).values_list('card', flat=True)

        # Get unplayed cards
        remaining_cards = Card.objects.exclude(id__in=played_cards)
        remaining_cards_list = [f"{card.rank} of {card.suit}" for card in remaining_cards]

        return {"remaining_cards": remaining_cards_list}  # Instead of JsonResponse

    except Exception as e:
        print(f"Error updating remaining cards frontend: {str(e)}")


def start_euchre_round(game):
    """
    Plays all 5 tricks in one request and returns the final round results.
    """
    players = list(Player.objects.all())  # Fetch players
    player_hands = {player: [] for player in players}  # Initialize hands

    # Fetch latest hand from the game
    latest_hand = Hand.objects.filter(game=game).order_by('-id').first()
    if not latest_hand:
        return JsonResponse({"error": "No hand found for the current game!"}, status=400)

    # Retrieve unplayed cards for each player
    unplayed_cards = PlayedCard.objects.filter(hand=latest_hand, player__in=players)
    for played_card in unplayed_cards:
        player_hands[played_card.player].append(played_card.card)

    # Ensure all players have enough cards to play
    for player in players:
        if len(player_hands[player]) < 5:
            return JsonResponse({"error": f"{player.name} has {len(player_hands[player])} cards instead of 5!"}, status=400)

    # Track tricks won by each team
    team1_tricks = 0  # Player + Bot2
    team2_tricks = 0  # Bot1 + Bot3
    tricks_data = []  # Store all trick results

    # Play all 5 tricks in a loop
    for trick_number in range(5):
        trick_cards = []  # Cards played in this trick
        hand = Hand.objects.create(game=game, dealer=game.dealer, trump_suit=game.trump_suit)

        # Players play in order
        for player in players:
            card_to_play = determine_best_card(player_hands[player], hand.trump_suit, trick_cards)
            play_card(player, hand, card_to_play, player_hands, game)
            trick_cards.append(PlayedCard(player=player, hand=hand, card=card_to_play, order=len(trick_cards) + 1))

        # Determine the winner of the trick
        trick_winner = evaluate_trick_winner(hand.trump_suit, trick_cards)
        hand.winner = trick_winner
        hand.save()

        # Assign trick points
        if trick_winner.name in ["Player", "Team Mate"]:
            team1_tricks += 1
        else:
            team2_tricks += 1

        # Store trick results
        tricks_data.append({
            "trick_number": trick_number + 1,
            "players": [pc.player.name for pc in trick_cards],
            "cards": [f"{pc.card.rank} of {pc.card.suit}" for pc in trick_cards],
            "winner": trick_winner.name
        })

    # Update the game results after all tricks
    update_game_results(game, team1_tricks, team2_tricks)

    # Return the final round results
    return JsonResponse({
        "message": "Round completed.",
        "tricks": tricks_data,  # Send all tricks at once
        "round_results": {
            "team1_points": game.team1_points,
            "team2_points": game.team2_points,
            "winning_team": "Team 1" if game.team1_points >= 10 else "Team 2" if game.team2_points >= 10 else None,
        }
    })






# def start_euchre_round(game):
#     """
#     Start a Euchre round using the players' existing hands.
#     """

#     # Retrieve all players
#     player_objects = Player.objects.all()
#     player_list = list(player_objects)  # Convert to list for proper filtering

#     # Initialize player hands from PlayedCard
#     player_hands = {player: [] for player in player_objects}

#     # Debug: Print current hand sizes before fetching cards
#     for player, cards in player_hands.items():
#         print(f"{player.name} has {len(cards)} cards BEFORE retrieval.")

#     # Fetch latest hand from the game
#     latest_hand = Hand.objects.filter(game=game).order_by('-id').first()

#     if not latest_hand:
#         print("Error: No hand found for the current game!")
#         return  # Prevents continuing with a broken state

#     print(f"Using Hand ID: {latest_hand.id} for retrieving cards.")

#     # Fetch PlayedCards only for this hand and these players
#     unplayed_cards = PlayedCard.objects.filter(hand=latest_hand, player__in=player_list)

#     if unplayed_cards.count() == 0:
#         print("UnplayedCards is empty! Investigating...")
#         print(f"Total PlayedCard objects in DB: {PlayedCard.objects.count()}")
#         print(f"Total PlayedCard objects for this hand: {PlayedCard.objects.filter(hand=latest_hand).count()}")
#         print(f"Expected hand ID: {latest_hand.id}")

#     # Assign cards to player_hands
#     for played_card in unplayed_cards:
#         player_hands[played_card.player].append(played_card.card)

#     # Debugging: Check card assignments
#     for player, cards in player_hands.items():
#         print(f"{player.name} has {len(cards)} cards AFTER retrieval.")

#     # Ensure all players have 5 cards before starting the round
#     for player in player_objects:
#         player_cards = player_hands[player]
#         if len(player_cards) < 5:
#             raise ValueError(f"{player.name} has {len(player_cards)} cards instead of 5!")

#     # # Play hands
#     # for _ in range(5):  # Assuming 5 hands in the game
#     #     hand = Hand.objects.create(game=game, dealer=game.dealer, trump_suit=game.trump_suit)

#     #     for player in player_objects:
#     #             if player.is_human:
#     #                 # Human player logic (UI interaction needed here)
#     #                 continue
#     #             else:
#     #             if not player_hands[player]:
#     #                 raise ValueError(f"{player.name} has no cards to play.")

#     #             # Bot logic to play the best card
#     #             card_to_play = determine_best_card(player_hands[player], hand.trump_suit, hand.played_cards.all())

#     #             # Check if card_to_play is valid
#     #             if card_to_play is None:
#     #                 raise ValueError(f"{player.name} has no valid card to play.")

#     #             # Log the card being played (optional)
#     #             print(f"{player.name} is playing {card_to_play.rank} of {card_to_play.suit}.")

#     #             # Play the card
#     #             play_card(player, hand, card_to_play, player_hands, game)

#     #     # Determine winner of the trick
#     #     hand.winner = evaluate_trick_winner(hand.trump_suit, hand.played_cards.all())
#     #     hand.save()
    
#      # Play hands (Player included)
#     for _ in range(5):  # Assuming 5 hands in the game
#         hand = Hand.objects.create(game=game, dealer=game.dealer, trump_suit=game.trump_suit)

#         for player in player_objects:
#             if not player_hands[player]:
#                 raise ValueError(f"{player.name} has no cards to play.")

#             # **Player now plays automatically like a bot**
#             card_to_play = determine_best_card(player_hands[player], hand.trump_suit, hand.played_cards.all())

#             if card_to_play is None:
#                 raise ValueError(f"{player.name} has no valid card to play.")

#             print(f"{player.name} is playing {card_to_play.rank} of {card_to_play.suit}.")

#             # Play the card (automatically for Player and AI)
#             play_card(player, hand, card_to_play, player_hands, game)

#         # Determine winner of the trick
#         hand.winner = evaluate_trick_winner(hand.trump_suit, hand.played_cards.all())
#         hand.save()


#     # Finalize results for this round
#     update_game_results(game)

#     # Now delete played cards (moved to end, after game logic runs)
#     PlayedCard.objects.filter(hand__game=game).delete()

    # If no team has reached 10 points, start another trump selection process
    # if game.team1_points < 10 and game.team2_points < 10:
    #     # Fetch round results
    #     results = {
    #         "team1_points": game.team1_points,
    #         "team2_points": game.team2_points,
    #         "winning_team": "Team 1" if game.team1_points >= 10 else "Team 2" if game.team2_points >= 10 else None,
    #     }
    #     # Return results for end of round dialog
    #     return JsonResponse({
    #         "message": "Round completed.",
    #         "round_results": results
    #     })
    # else:
    #     print(f"Game over! Winner: {'Team 1' if game.team1_points >= 10 else 'Team 2'}")
