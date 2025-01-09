from django.db import models
from django.db.models import Max
from random import shuffle


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
    hand = models.ForeignKey(Hand, on_delete=models.CASCADE, related_name='played_cards')
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    order = models.IntegerField()  # Order in which the card was played in the hand

    def __str__(self):
        return f"{self.player.name} played {self.card} in Hand {self.hand.id}"


class GameResult(models.Model):
    game = models.OneToOneField(Game, on_delete=models.CASCADE)
    winner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='won_games')
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


def assign_trump(deck, trump_suit):
    """
    Marks cards in the deck as trump cards based on the trump suit.
    """
    for card in deck:
        card.is_trump = card.suit == trump_suit
        card.save()
    

def determine_best_card(hand, trump_suit, played_cards):
    """
    Determine the best card for a bot to play based on the current hand and game state.
    
    Args:
        hand (list of Card): Cards currently in the bot's hand.
        trump_suit (str): The trump suit for the current hand.
        played_cards (list of PlayedCard): Cards that have been played so far in the current trick.
    
    Returns:
        Card: The best card to play.
    """
    if not hand:
        raise ValueError("Hand is empty, no card can be played.")
    
    lead_suit = played_cards[0].card.suit if played_cards else None

    # Filter cards based on lead suit
    suited_cards = [card for card in hand if card.suit == lead_suit]
    trump_cards = [card for card in hand if card.suit == trump_suit]

    # Play a suited card if available
    if suited_cards:
        return max(suited_cards, key=lambda x: x.rank)

    # Play a trump card if no suited cards are available
    if trump_cards:
        return max(trump_cards, key=lambda x: x.rank)

    # If no suited or trump cards, play the lowest-ranked card
    return min(hand, key=lambda x: x.rank)

    
def evaluate_trick_winner(trump_suit, played_cards):
    """
    Determines the winner of the current trick.
    Args:
        trump_suit (str): The trump suit for the current hand.
        played_cards (QuerySet): The cards that have been played in the trick.

    Returns:
        Player: The player who won the trick.
    """
    if not played_cards:
        return None

    # Find trump cards
    trump_cards = [pc for pc in played_cards if pc.card.suit == trump_suit]
    if trump_cards:
        winning_card = max(trump_cards, key=lambda x: x.card.rank)
    else:
        # Find cards matching the lead suit
        lead_suit = played_cards[0].card.suit
        suited_cards = [pc for pc in played_cards if pc.card.suit == lead_suit]
        winning_card = max(suited_cards, key=lambda x: x.card.rank)

    # Return the player who played the winning card
    return winning_card.player


def update_game_results(game):
    """
    Updates the game results based on hands played.
    Assigns the human player as the winner if the human's team wins,
    otherwise assigns a bot from the winning team.
    """
    results = {"team1": 0, "team2": 0}
    
    # Iterate through each hand to calculate team scores
    for hand in game.hands.all():
        winning_player = hand.winner
        if winning_player.name in ["Human", "Bot2"]:  # Team 1: Human + Bot2
            results["team1"] += 1
        else:  # Team 2: Bot1 + Bot3
            results["team2"] += 1

    # Determine which team wins
    if results["team1"] > results["team2"]:
        winning_player = Player.objects.get(name="Human")  # Human's team wins
    else:
        winning_player = Player.objects.filter(name__in=["Bot1", "Bot3"]).first()  # Bot's team wins

    # Create the game result
    GameResult.objects.create(
        game=game,
        winner=winning_player,  # Assign the human or bot as the winner
        total_hands=len(game.hands.all()),
        points=results
    )
    

def play_card(player, hand, card, player_hands):
    """
    Plays a card for a player, removing it from their hand and adding it to the PlayedCard model.
    Args:
        player (Player): The player who is playing the card.
        hand (Hand): The current hand being played.
        card (Card): The card to play.
        player_hands (dict): A dictionary mapping players to their current hands.
    """
    if card not in player_hands[player]:
        raise ValueError(f"{card} is not in {player.name}'s hand.")

    # Record the played card in the database
    PlayedCard.objects.create(
        hand=hand,
        player=player,
        card=card,
        order=len(hand.played_cards.all()) + 1
    )

    # Remove the card from the player's hand
    player_hands[player].remove(card)
    
def start_round(game):
    """
    Shuffles the deck, deals one card to each player, and determines the dealer.
    """
    # Get players in the game
    players = Player.objects.all()

    # Copy and shuffle the deck
    deck = list(Card.objects.all())
    shuffle(deck)

    # Ensure there are enough cards
    if len(deck) < len(players):
        raise ValueError("Not enough cards in the deck to determine the dealer.")

    # Deal one card to each player
    dealt_cards = {}
    for player in players:
        dealt_cards[player] = deck.pop()

    # Find the highest card
    def card_rank_value(card):
        rank_order = ['9', '10', 'J', 'Q', 'K', 'A']
        return rank_order.index(card.rank)

    if dealt_cards:
        highest_card = max(dealt_cards.values(), key=card_rank_value)
        dealer = next(player for player, card in dealt_cards.items() if card == highest_card)
    else:
        highest_card = None
        dealer = None

    # Return results, including highest_card
    return dealt_cards, dealer, highest_card

def deal_hand(deck, players):
    """
    Deals a hand of 5 cards to each player without modifying the database.
    """
    hands = {}
    for player in players:
        if len(deck) < 5:
            raise ValueError("Not enough cards in the deck to deal a hand.")
        hands[player] = [deck.pop() for _ in range(5)]  # Each player gets 5 cards
    return hands

def start_euchre_game():
    players = [
        {"name": "Player", "is_human": True},
        {"name": "Opponent1", "is_human": False},
        {"name": "Team Mate", "is_human": False},
        {"name": "Opponent2", "is_human": False},
    ]

    # Initialize the game and create a fresh deck
    game, deck = initialize_game(players)
    player_objects = Player.objects.all()

    # Determine the dealer
    dealt_cards, dealer, highest_card = start_round(game)

    # Deal a full hand to each player
    hands = deal_hand(deck, player_objects)

    return game, hands, dealer