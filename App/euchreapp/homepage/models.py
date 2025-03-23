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
    team = models.IntegerField(default=0)
    partner = models.CharField(max_length=100, default="")

    def __str__(self):
        return self.name

    def determine_trump(self, hand, dealer, up_card, player_order, trump_round):
        """
        Determines the trump suit by scoring their hand and comparing it to the thresholds for their position
        """
        # TODO: Add taking into account the up card rank and who it is going to (maybe would just affect the position thresholds? Like if it is a bower, dealer position threshold goes down)
        
        trump_suit = up_card.suit
        position = self.get_seat_position(player_order)

        if trump_round == "1":
            # If you are dealer, in the first round, your hand should contain the up card and discard a card
            if self.name == dealer.name:
                # Dealer should analyze their hand as if they already picked up the up card
                print(f"Dealer {self.name} analyzing hand as if they already picked up the up card")
                temp_hand = list(hand)
                temp_hand.append(up_card)

                # Discard a card
                discarded_card = self.dealer_discard(temp_hand, up_card.suit)
                temp_hand.remove(discarded_card)

                hand_score = self.evaluate_hand(temp_hand, trump_suit)
                print(f"Dealer {self.name} hand score: {hand_score}")
            else:
                hand_score = self.evaluate_hand(hand, trump_suit)
                print(f"Player {self.name} hand score: {hand_score}")

            first_round_position_thresholds = {
                'first': 0.42,
                'second': 0.35,
                'third': 0.44,
                'dealer': 0.375
            }

            threshold = first_round_position_thresholds[position]
            
            return trump_suit if hand_score >= threshold else 'pass'
        
        if trump_round == "2":

            second_round_thresholds = {
                'first': {
                    'next': 0.275,
                    'reverse': 0.4
                },
                'second': {
                    'next': 0.45,
                    'reverse': 0.275
                },
                'third': {
                    'next': 0.3,
                    'reverse': 0.375
                },
                'dealer': {
                    'next': 0.35,
                    'reverse': 0.25
                }
            }

            next_suit = up_card.next_suit()

            suits = ["hearts", "diamonds", "clubs", "spades"]
            reverse_suits = [suit for suit in suits if suit not in [trump_suit, next_suit]]

            seat_thresholds = second_round_thresholds[position]

            # TODO: Do not just choose next suit if greater than threshold, also consider reverse suit (Maybe check how much higher the difference between the threshold and the score is)

            next_suit_score = self.evaluate_hand(hand, next_suit)
            reverse_suit_score_1 = self.evaluate_hand(hand, reverse_suits[0])
            reverse_suit_score_2 = self.evaluate_hand(hand, reverse_suits[1])
            
            if self.name == dealer.name:
                options = [
                    (next_suit, next_suit_score),
                    (reverse_suits[0], reverse_suit_score_1),
                    (reverse_suits[1], reverse_suit_score_2)
                ]

                best_suit, _ = max(options, key=lambda x: x[1])
                return best_suit

            should_call_next = next_suit_score >= seat_thresholds['next']
            should_call_reverse = reverse_suit_score_1 >= seat_thresholds['reverse'] or reverse_suit_score_2 >= seat_thresholds['reverse']

            # If all suits are higher than threshold, choose the suit that is greater than the threshold by the most
            if should_call_next and should_call_reverse:
                if next_suit_score - seat_thresholds['next'] >= reverse_suit_score_1 - seat_thresholds['reverse'] or reverse_suit_score_2 - seat_thresholds['reverse']:
                    return next_suit
                else:
                    return reverse_suits[0] if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suits[1]
            elif should_call_next:
                return next_suit
            elif should_call_reverse:
                return reverse_suits[0] if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suits[1]
            
            return 'pass'
        
    def get_seat_position(self, player_order):
        """
        Returns the position of the player in the player order
        """
        positions = ['first', 'second', 'third', 'dealer']

        for i, p in enumerate(player_order):
            if p == self:
                return positions[i]

    def evaluate_hand(self, hand, trump_suit):
        """
        Evaluates the strength of the hand based on the trump suit, aces, and suit voids, multiplying each by the strategy weights
        """
        strategy_weights = {
            'trump_cards': 0.5,
            'off_aces': 0.4,
            'num_suits': 0.1
            # 'seat_position': 0.2
        }
        
        score = 0

        # Evaluate strength of trump cards
        trump_strength = self.evaluate_trump(hand, trump_suit)
        score += trump_strength * strategy_weights['trump_cards']

        # Evaluate strength of Aces
        aces_strength = self.evaluate_aces(hand, trump_suit)
        score += aces_strength * strategy_weights['off_aces']


        # Evaluate suit voids
        voids_strength = self.evaluate_voids(hand, trump_suit)
        score += voids_strength * strategy_weights['num_suits']

        return score

    def evaluate_trump(self, hand, trump_suit):
        """
        Evaluates the strength of the trump cards in the hand by adding their values together and normalizing to 0-1
        """
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down, so should be evaluated differently (Same with Jacks if a bower was turned down the JA are top two, not JJ)
        # TODO: Dealer should be evaluated differently: you pick up the up card and discard so hand should evaluated differently

        trump_sum = 0

        for card in hand:
            if card.is_right_bower(trump_suit):
                trump_sum += 1
            elif card.is_left_bower(trump_suit):
                trump_sum += 0.9
            elif card.suit == trump_suit:
                trump_ranks = {"A": 0.8, "K": 0.7, "Q": 0.6, "10": 0.5, "9": 0.4}
                trump_sum += trump_ranks[card.rank]

        return trump_sum / 4 # Normalize value to 0-1 (max score is 4)

    def evaluate_aces(self, hand, trump_suit):
        """
        Evaluates the strength of the aces in the hand by adding 1 per ace and normalizing to 0-1
        """
        # TODO: Add evaluation for doubletons (Kx, Qx) as those should be evaluated differently (could become sorta like aces)
        # TODO: Add ranking based on how many cards are the same suit as Aces (Aces are more valuable if they are the only card of their suit) (AK is also valuable though so should not be penalized)
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down
        aces_sum = 0
        for card in hand:
            if card.rank == "A" and card.suit != trump_suit:
                if card.suit == card.next_suit():
                    # Aces of the "next" suit are less valuable because there are less cards in that suit
                    aces_sum += 0.9
                else:
                    aces_sum += 1
        return aces_sum / 2.9 # Normalize value to 0-1 (max score is 2.9)

    def evaluate_voids(self, hand, trump_suit):
        """
        Evaluates the strength of the suit voids in the hand by counting the number of suits that are not in the hand and normalizing to 0-1
        """

        suits = set(card.suit for card in hand)

        if trump_suit not in suits:
            # If you don't have trump, voids are not valuable
            num_suits = 4
        else:
            num_suits = len(suits)
        
        return (4-num_suits) / 3 # Normalize value to 0-1 (max score is 3)
    
    # def determine_random_card(self, hand, trump_suit, played_cards):
    #     """
    #     Determines a random card to play that is valid
    #     """
    #     if not played_cards:
    #         return hand[0]
        
    #     lead_suit = played_cards[0].card.suit
    #     valid_cards = [card for card in hand if card.card.suit == lead_suit]
    #     if valid_cards:
    #         return valid_cards[0]
        
    #     return hand[0]

    def determine_best_card(self, hand, trump_suit, played_cards, previous_cards, trump_caller):
        """
        Determines the best card to play in a trick
        """

        partner_called_trump = trump_caller.name == self.partner
        player_called_trump = trump_caller.name == self.name
        opponent_called_trump = not partner_called_trump and not player_called_trump # TODO: It can be useful to know which opponent called trump specifically as that can change the card to play

        # Check if you are leading
        if not played_cards:
            # Decide what card to lead
            return self.choose_lead_card(hand, trump_suit, previous_cards, partner_called_trump, player_called_trump, opponent_called_trump)
        
        # Not leading, so get suit that was lead
        if played_cards[0].card.is_left_bower(trump_suit):
            lead_suit = played_cards[0].card.next_suit()
        else:
            lead_suit = played_cards[0].card.suit

        # Find winner of current trick
        winning_played_card = max(played_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit, lead_suit))
        current_winner = winning_played_card.player.name
        
        is_partner_winning = current_winner == self.partner
        player_is_last_to_play = len(played_cards) == 3

        # Gather cards by suit
        trump_cards = self.get_trump_cards(hand, trump_suit)
        # If the lead suit is trump, get all trump cards, otherwise get all lead suit cards
        if lead_suit == trump_suit:
            lead_suit_cards = trump_cards
        else:
            lead_suit_cards = [card for card in hand if card.suit == lead_suit and not card.is_left_bower(trump_suit)]

        # Get lowest card in hand
        lowest_card = min(hand, key=lambda x: Card.euchre_rank(x, trump_suit, lead_suit))

        if lead_suit_cards:
            high_lead = max(lead_suit_cards, key=lambda x: Card.euchre_rank(x, trump_suit, lead_suit))
            low_lead = min(lead_suit_cards, key=lambda x: Card.euchre_rank(x, trump_suit, lead_suit))

            # Follow suit
            if is_partner_winning:
                if player_is_last_to_play:
                    # Partner already has the trick won, so play lowest card
                    return low_lead
                elif self.is_boss_card(winning_played_card.card, previous_cards):
                    # If partner is winning with a boss card, play lowest card
                    return low_lead
                else:
                    # If partner is not winning with a boss card, play highest card if you can win trick
                    if Card.euchre_rank(high_lead, trump_suit) > Card.euchre_rank(winning_played_card.card, trump_suit):
                        return high_lead
            else:
                # Opponent is winning, so play highest card if you can win trick
                if Card.euchre_rank(high_lead, trump_suit) > Card.euchre_rank(winning_played_card.card, trump_suit):
                    return high_lead
                
            return low_lead
        
        played_trump_cards = self.get_trump_cards([card.card for card in played_cards], trump_suit)
        
        if not played_trump_cards:
            if trump_cards:
                small_trump = min(trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))
                if is_partner_winning:
                    if player_is_last_to_play:
                        return lowest_card
                    elif not self.is_boss_card(winning_played_card.card, previous_cards):
                        # Partner is winning, but not with a good card, so play small trump
                        return small_trump
                    return lowest_card
                else:
                    # Opponent is winning, so play small trump
                    return small_trump
            else:
                # Player has no trump cards, so play lowest card
                return lowest_card
                
        # Trump cards have been played
        if is_partner_winning:
            # Partner is winning with a trump card
            return lowest_card
        else:
            # Opponent is winning with a trump card
            winning_trump_cards = [card for card in trump_cards if Card.euchre_rank(card, trump_suit) > Card.euchre_rank(winning_played_card.card, trump_suit)]
            if winning_trump_cards:
                # Play the highest trump necessary to take the lead
                return min(winning_trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))
            else:
                # Cannot win trick, so play lowest card # TODO: making a void could be more valuable than playing lowest card
                return lowest_card  

    def choose_lead_card(self, hand, trump_suit, previous_cards, partner_called_trump, player_called_trump, opponent_called_trump):
        """
        Determines the best card to lead with
        """
        trump_cards = self.get_trump_cards(hand, trump_suit)

        # Get all cards that are the highest card in the suit remaining
        boss_cards = self.get_boss_cards_in_hand(hand, previous_cards)
        non_trump_boss = [card for card in boss_cards if card.suit != trump_suit]

        # Lead strong if partner called trump
        if partner_called_trump and trump_cards:
            return max(trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))

        # If you called trump and have highest trump, lead it
        if player_called_trump:
            have_highest_trump = self.has_boss_card(hand, trump_suit, previous_cards)
            if have_highest_trump:
                return max(trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))
            elif len(trump_cards) > 1:
                return min(trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))

        # If opponents called, lead boss off suit if you have it or lead low
        if opponent_called_trump:
            if non_trump_boss:
                return max(non_trump_boss, key=lambda x: Card.euchre_rank(x, trump_suit))
            else:
                return min(hand, key=lambda x: Card.euchre_rank(x, trump_suit))
            
        # Lead highest off suit if it is a boss card
        if boss_cards:
            if non_trump_boss:
                return max(non_trump_boss, key=lambda x: Card.euchre_rank(x, trump_suit))

        # Otherwise, simply lead lowest card
        return min(hand, key=lambda x: Card.euchre_rank(x, trump_suit))

    def get_boss_cards_in_hand(self, hand, previous_cards):
        """
        Determines all boss cards in hand
        """
        boss_cards = []
        for card in hand:
            if self.is_boss_card(card, previous_cards):
                boss_cards.append(card)
        return boss_cards
    
    def get_boss_card(self, suit, previous_cards, is_trump=False):
        """
        Determines the highest card of the highest rank remaining in the suit
        """
        card_ranks = ["A", "K", "Q", "J", "10", "9"]

        if is_trump:
            temp_card = Card.objects.get(rank="J", suit=suit)
            # Deal with bowers
            if not any(played_card.card.is_right_bower(suit) for played_card in previous_cards):
                return temp_card
            elif not any(played_card.card.is_left_bower(suit) for played_card in previous_cards):
                return Card.objects.get(rank="J", suit=temp_card.next_suit()) # should be next suit

            # Both bowers have been played already    
            card_ranks.remove("J")

        # Get all previous cards of the relevant suit
        relevant_previous_cards = [card for card in previous_cards if card.card.suit == suit]

        for card in relevant_previous_cards:
            if card.card.rank in card_ranks:
                card_ranks.remove(card.card.rank)

        return Card.objects.get(rank=card_ranks[0], suit=suit) if card_ranks else None
        
    def is_boss_card(self, card, previous_cards):
        """
        Determines if a card is the highest card of the highest rank remaining in the suit
        """
        highest_card = self.get_boss_card(card.suit, previous_cards, card.is_trump)

        return card.rank == highest_card.rank and card.suit == highest_card.suit

    def has_boss_card(self, hand, suit, previous_cards):
        """
        Determines if the hand has a boss card in the given suit
        """
        highest_card = self.get_boss_card(suit, previous_cards)

        if not highest_card:
            return False

        return any(card.rank == highest_card.rank and card.suit == highest_card.suit for card in hand)
                
    def get_trump_cards(self, hand, trump_suit):
        return [card for card in hand if card.suit == trump_suit or card.is_left_bower(trump_suit)]

    def dealer_discard(self, dealer_hand, trump_suit):
        """
        Choose a card to discard based on creating a suit void if possible
        """
        trump_cards = self.get_trump_cards(dealer_hand, trump_suit)
        non_trump_cards = [card for card in dealer_hand if card not in trump_cards]

        if not non_trump_cards:
            # Hand is all trump cards, so discard lowest trump card
            return min(trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))
        
        # Find a possible void
        suit_counts = {}
        for card in non_trump_cards:
            suit = card.suit
            if suit not in suit_counts:
                suit_counts[suit] = []
            suit_counts[suit].append(card)

        # Find any suits with only one card (not Aces)
        possible_voids = [
            cards[0] for suit, cards in suit_counts.items()
            if len(cards) == 1 and cards[0].rank != "A"
        ]

        if possible_voids:
            # Choose the lowest card of the possible voids
            return min(possible_voids, key=lambda x: Card.euchre_rank(x, trump_suit))
        
        # If no possible voids, discard lowest non-trump card
        return min(non_trump_cards, key=lambda x: Card.euchre_rank(x, trump_suit))


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
    
    SUITS_PAIRS = {
        'hearts': 'diamonds',
        'diamonds': 'hearts',
        'clubs': 'spades',
        'spades': 'clubs'
    }

    suit = models.CharField(max_length=10, choices=SUITS)
    rank = models.CharField(max_length=5, choices=RANKS)
    is_trump = models.BooleanField(default=False)

    class Meta:
        unique_together = ('suit', 'rank')  # Prevent duplicates

    def __str__(self):
        return f"{self.rank} of {self.suit}" + (" (Trump)" if self.is_trump else "")
        
    def next_suit(self):
        return self.SUITS_PAIRS[self.suit]
        
    def is_right_bower(self, trump_suit):
        return self.suit == trump_suit and self.rank == "J"
    
    def is_left_bower(self, trump_suit):
        return self.suit == self.SUITS_PAIRS[trump_suit] and self.rank == "J"

    @staticmethod
    def euchre_rank(card, trump_suit, lead_suit=None):
        """ Assigns rank values based on Euchre hierarchy. """
        if card.is_right_bower(trump_suit):
            return 25  # Right Bower (Highest)
        elif card.is_left_bower(trump_suit):
            return 24  # Left Bower
        if card.suit == trump_suit:
            return 15 + ["9", "10", "Q", "K", "A"].index(card.rank)
        if card.suit == lead_suit:
            return 6 + ["9", "10", "J", "Q", "K", "A"].index(card.rank)
        return ["9", "10", "J", "Q", "K", "A"].index(card.rank)

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
        print(f"🔥 DEBUG: Kitty after dealing: {deck}")

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

    # Follow suit if possible
    if lead_suit_cards:
        return max(lead_suit_cards, key=Card.euchre_rank(card, trump_suit, lead))

    # Otherwise, play the best trump if available
    if trump_cards:
        return max(trump_cards, key=Card.euchre_rank(card, trump_suit))

    # Otherwise, play the lowest non-trump card
    return min(other_cards, key=Card.euchre_rank(card, trump_suit))



def evaluate_trick_winner(trump_suit, played_cards):
    """
    Determines the winner of the current trick based on Euchre rules.
    """
    if not played_cards:
        return None

    if played_cards[0].card.is_left_bower(trump_suit):
        lead_suit = played_cards[0].card.next_suit()
    else:
        lead_suit = played_cards[0].card.suit

    for pc in played_cards:
        print(f"Card: {pc}")

    # Find the highest-ranked card
    winning_card = max(played_cards, key=lambda pc: Card.euchre_rank(pc.card, trump_suit, lead_suit))
    return winning_card.player



def update_game_results(game, team1_tricks, team2_tricks, trump_caller):
    """
    Updates game results after each round based on tricks won.
    """
    if trump_caller.team == 1:
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
    Rotates the dealer to the next player in the sequence.
    """
    players = list(Player.objects.all())

    if not game.dealer:
        return players[0]  # Default to first player if no dealer is set

    dealer_index = players.index(game.dealer)
    next_dealer_index = (dealer_index + 1) % len(players)
    new_dealer = players[next_dealer_index]

    print(f"✅ Dealer rotated to: {new_dealer.name}")  # Debugging output

    return new_dealer



def rotate_dealer(game):
    """
    Rotates the dealer to the next player in the sequence.
    """
    players = list(Player.objects.all())
    if not game.dealer:
        return players[0]  # Default to first player if no dealer is set

    dealer_index = players.index(game.dealer)
    next_dealer_index = (dealer_index + 1) % len(players)  # Move to next player
    new_dealer = players[next_dealer_index]

    # Debugging
    print(f"Dealer rotated to: {new_dealer.name}")

    return new_dealer


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
    previous_cards = []

    # Left of the dealer leads the first trick
    dealer_index = players.index(game.dealer)
    trick_leader = players[(dealer_index + 1) % len(players)]

    # Play all 5 tricks in a loop
    for trick_number in range(5):
        trick_cards = []  # Cards played in this trick
        hand = Hand.objects.create(game=game, dealer=game.dealer, trump_suit=game.trump_suit or None)

        # Whoever won the trick plays first
        leader_index = players.index(trick_leader)
        player_order = players[leader_index:] + players[:leader_index]

        print(f"\nTrick number: {trick_number}")
        print(f"Player order: {player_order}")

        # Players play in order
        for player in player_order:
            card_to_play = player.determine_best_card(player_hands[player], hand.trump_suit, trick_cards, previous_cards, trump_caller)
            play_card(player, hand, card_to_play, player_hands, game)
            trick_cards.append(PlayedCard(player=player, hand=hand, card=card_to_play, order=len(trick_cards) + 1))

        # Determine the winner of the trick
        trick_winner = evaluate_trick_winner(hand.trump_suit, trick_cards)
        hand.winner = trick_winner
        hand.save()

        # Whoever won the trick leads the next trick
        trick_leader = trick_winner

        # Assign trick points
        if trick_winner.team == 1:
            team1_tricks += 1
        else:
            team2_tricks += 1

        previous_cards.extend(trick_cards)

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
