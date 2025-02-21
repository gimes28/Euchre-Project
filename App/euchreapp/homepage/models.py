from django.db import models
from django.db.models import Max
from random import shuffle
from django.http import JsonResponse
import time
import traceback


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
    trump_suit = models.CharField(
        max_length=10,
        choices=[('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')],
        null=True, blank=True  # ✅ Allows null values when resetting
    )
    team1_points = models.IntegerField(default=0)  # Points for Human + Bot2
    team2_points = models.IntegerField(default=0)  # Points for Bot1 + Bot3

    def __str__(self):
        return f"Game {self.id} started at {self.created_at}"


class Hand(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='hands')
    dealer = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='dealt_hands')
    trump_suit = models.CharField(
        max_length=10,
        choices=[('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')],
        null=True, blank=True  # ✅ Allow null values when resetting the game
    )
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

    @property
    def suit_name(self):
        return dict(self.SUITS)[self.suit]


class PlayedCard(models.Model):
    hand = models.ForeignKey(Hand, on_delete=models.CASCADE, related_name='played_cards', null=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    order = models.IntegerField()

    # REMOVE UNIQUE CONSTRAINT
    class Meta:
        unique_together = None  # REMOVE ANY UNIQUE CONSTRAINTS ON THIS MODEL

    def __str__(self):
        return f"{self.player.name} played {self.card.rank} of {self.card.suit} in Game {self.hand.game.id}"


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



def deal_hand(deck, players, game):
    """
    Deals a hand of 5 unique cards to each player while ensuring no duplicate assignments.
    """
    try:
        print("📢 deal_hand() function was called!")  

        if not game:
            print("🚨 ERROR: No active game found!")
            return {}, []

        # **Step 1: Ensure we have enough unique cards**
        deck_size = len(deck)
        print(f"🔥 DEBUG: Deck size before dealing: {deck_size} (Expected: 24 cards)")

        if deck_size < len(players) * 5:
            return JsonResponse({"error": "Not enough unique cards left in deck!"}, status=500)

        # **Step 2: Create a new hand**
        hand = Hand.objects.create(game=game, dealer=game.dealer, trump_suit=game.trump_suit or None)

        # **Step 3: Assign Cards**
        hands = {player: [] for player in players}
        assigned_cards = set()

        for _ in range(5):  
            for player in players:
                if not deck:
                    print("🚨 ERROR: Deck ran out of cards while dealing!")
                    return JsonResponse({"error": "🔥 ERROR: Ran out of unique cards while dealing!"}, status=500)

                card = deck.pop(0)

                while card in assigned_cards:
                    deck.append(card)  
                    if not deck:
                        print("🚨 ERROR: No more available unique cards!")
                        return JsonResponse({"error": "🔥 ERROR: No more available unique cards!"}, status=500)
                    card = deck.pop(0)

                assigned_cards.add(card)
                hands[player].append(card)

                PlayedCard.objects.create(
                    player=player,
                    card=card,
                    hand=hand,
                    order=len(hands[player])
                )

        # Debugging: Print hands before returning
        print(f"🔥 DEBUG: Hands dealt: {hands}")

        return hands, deck  # **Ensure this returns a tuple of (hands, remaining_cards)**

    except Exception as e:
        print(f"🚨 ERROR in deal_hand(): {str(e)}")
        return {}, []




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



def update_game_results(game, team1_tricks, team2_tricks, trump_caller):
    """
    Updates game results after each round based on tricks won.
    """
    if trump_caller in ["Player", "Team Mate"]:
        trump_calling_team = 1
    else:
        trump_calling_team = 2

    if team1_tricks >= 3:
        if trump_calling_team == 1:
            # Team 1 called trump and won
            game.team1_points += 1 if team1_tricks < 5 else 2
        else:
            # Team 1 euchred the other team
            game.team1_points += 2
    if team2_tricks >= 3:
        if trump_calling_team == 2:
            # Team 2 called trump and won
            game.team2_points += 1 if team2_tricks < 5 else 2
        else:
            # Team 2 euchred the other team
            game.team2_points += 2

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



def start_euchre_round(game, trump_caller):
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
        hand = Hand.objects.create(game=game, dealer=game.dealer, trump_suit=game.trump_suit or None)

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
    update_game_results(game, team1_tricks, team2_tricks, trump_caller)

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
