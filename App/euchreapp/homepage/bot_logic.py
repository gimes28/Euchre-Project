import pandas as pd
import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_storage")

FILENAME = os.path.join(DATA_DIR, "game_data.csv")

COLUMNS = [ "game_id", "round_id", "team1_score", "team2_score",
          "team1_round_score", "team2_round_score",
            "seat_position", "is_dealer", "partner_is_dealer",
            "trump_suit", "hand", "known_cards", "card_to_evaluate", 
            "card_to_play", "win_probability"
]
class Table():
  def init_table():
    # Create DataFrame
    df = pd.DataFrame([], columns=COLUMNS)
    df.to_csv(FILENAME, index=False, header=True)

  def update_table(game_state):
    # Create new df
    df = pd.DataFrame([game_state])

    # Save to CSV
    df.to_csv(FILENAME, mode='a', index=False, header=False)



class Player():
    def __init__(self, name, partner, team):
        self.name = name
        self.partner = partner
        self.team = team

    def __str__(self):
        return self.name

class Card():
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

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank} of {self.suit}"

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

class PlayedCard():
    def __init__(self, card, player):
        self.player = player
        self.card = card

    def __str__(self):
        return f"{self.player.name} has {self.card.rank} of {self.card.suit}"

    def __str__(self):
        return f"{self.card.rank} of {self.card.suit}"

    def __repr__(self):
        return str(f"{self.card.rank} of {self.card.suit}")


    def get_card(self):
        return str(f"{self.card.rank} of {self.card.suit}")

class Bot(Player):
    def __init__(self, name, partner, team):
        super().__init__(name, partner, team)
        self.strategy_weights = {
            'trump_cards': 0.5,
            'off_aces': 0.4,
            'num_suits': 0.1
            # 'seat_position': 0.2
        }

    def determine_trump(self, hand, dealer, up_card, player_order, trump_round):
        """
        Determines the trump suit by scoring their hand and comparing it to the thresholds for their position
        """
        # TODO: Add taking into account the up card rank and who it is going to (maybe would just affect the position thresholds? Like if it is a bower, dealer position threshold goes wayyyyy down)

        trump_suit = up_card.card.suit
        position = self.get_seat_position(player_order)

        if trump_round == "1":
            # If you are dealer, in the first round, your hand should contain the up card and discard a card
            if self.name == dealer.name:
                # Dealer should analyze their hand as if they already picked up the up card
                temp_hand = hand.copy()
                temp_hand = self.dealer_pickup(temp_hand, up_card, trump_suit)

                hand_score = self.evaluate_hand(temp_hand, trump_suit)
            else:
                hand_score = self.evaluate_hand(hand, trump_suit)

            first_round_position_thresholds = {
                'first': 0.55,
                'second': 0.45,
                'third': 0.60,
                'dealer': 0.40
            }

            threshold = first_round_position_thresholds[position]

            if hand_score >= threshold:
                #for card in hand:
                  #print(f"{card}")
                #print(f"{hand_score} >= {first_round_position_thresholds[position]}")
                #print(f"Round 1 {trump_suit}")
                return trump_suit
            else:
                return 'pass'

        if trump_round == "2":

            second_round_thresholds = {
                'first': {
                    'next': 0.4,
                    'reverse': 0.4
                },
                'second': {
                    'next': 0.35,
                    'reverse': 0.30
                },
                'third': {
                    'next': 0.4,
                    'reverse': 0.4
                },
                'dealer': {
                    'next': 0.01,
                    'reverse': 0.01
                }
            }

            next_suit = up_card.card.next_suit()

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

                best_suit, score = max(options, key=lambda x: x[1])

                #for card in hand:
                #  print(f"{card}")
                #print(f"{score} >= {seat_thresholds}")
                #print(f"Round 2 {best_suit}")
                return best_suit

            should_call_next = next_suit_score >= seat_thresholds['next']
            should_call_reverse = reverse_suit_score_1 >= seat_thresholds['reverse'] or reverse_suit_score_2 >= seat_thresholds['reverse']

            # If all suits are higher than threshold, choose the suit that is greater than the threshold by the most
            if should_call_next and should_call_reverse:
                if next_suit_score - seat_thresholds['next'] >= reverse_suit_score_1 - seat_thresholds['reverse'] or reverse_suit_score_2 - seat_thresholds['reverse']:
                    #for card in hand:
                    #  print(f"{card}")
                    #print(f"{next_suit_score} >= {seat_thresholds['next']}")
                    #print(f"Round 2 {next_suit}")
                    return next_suit
                else:
                    if reverse_suit_score_1 >= reverse_suit_score_2:
                      #for card in hand:
                      #  print(f"{card}")
                      #print(f"{reverse_suit_score_1} >= {seat_thresholds['reverse']}")
                      #print(f"Round 2 {next_suit}")
                      return reverse_suits[0]
                    else:
                      #for card in hand:
                      #  print(f"{card}")
                      #print(f"{reverse_suit_score_2} >= {seat_thresholds['reverse']}")
                      #print(f"Round 2 {next_suit}")
                      return reverse_suits[1]

            elif should_call_next:
                #for card in hand:
                #  print(f"{card}")
                #print(f"{next_suit_score} >= {seat_thresholds['next']}")
                #print(f"Round 2 {next_suit}")
                return next_suit
            elif should_call_reverse:
                if reverse_suit_score_1 >= reverse_suit_score_2:
                  #for card in hand:
                  #  print(f"{card}")
                  #print(f"{reverse_suit_score_1} >= {seat_thresholds['reverse']}")
                  #print(f"Round 2 {next_suit}")
                  return reverse_suits[0]
                else:
                  #for card in hand:
                  #  print(f"{card}")
                  #print(f"{reverse_suit_score_2} >= {seat_thresholds['reverse']}")
                  #print(f"Round 2 {next_suit}")
                  return reverse_suits[1]

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

        score = 0

        # Evaluate strength of trump cards
        trump_strength = self.evaluate_trump(hand, trump_suit)
        score += trump_strength * self.strategy_weights['trump_cards']
        # print("Trump Strength: ", trump_strength)

        # Evaluate strength of Aces
        aces_strength = self.evaluate_aces(hand, trump_suit)
        score += aces_strength * self.strategy_weights['off_aces']
        # print("Aces Strength: ", aces_strength)


        # Evaluate suit voids
        voids_strength = self.evaluate_voids(hand, trump_suit)
        score += voids_strength * self.strategy_weights['num_suits']
        # print("Voids Strength: ", voids_strength)

        # Evaluate seat position
        # seat_strength = self.evaluate_seat_position(player_position, dealer)
        # score += seat_strength * self.strategy_weights['seat_position']

        return score

    def evaluate_trump(self, hand, trump_suit):
        """
        Evaluates the strength of the trump cards in the hand by adding their values together and normalizing to 0-1
        """
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down, so should be evaluated differently (Same with Jacks if a bower was turned down the JA are top two, not JJ)
        # TODO: Dealer should be evaluated differently: you pick up the up card and discard so hand should evaluated differently

        trump_sum = 0

        for playedCard in hand:
            if playedCard.card.is_right_bower(trump_suit):
                trump_sum += 1
            elif playedCard.card.is_left_bower(trump_suit):
                trump_sum += 0.9
            elif playedCard.card.suit == trump_suit:
                trump_ranks = {"A": 0.8, "K": 0.7, "Q": 0.6, "10": 0.5, "9": 0.4}
                trump_sum += trump_ranks[playedCard.card.rank]

        return trump_sum / 4 # Normalize value to 0-1 (max score is 4)

    def evaluate_aces(self, hand, trump_suit):
        """
        Evaluates the strength of the aces in the hand by adding 1 per ace and normalizing to 0-1
        """
        # TODO: Add evaluation for doubletons (Kx, Qx) as those should be evaluated differently (could become sorta like aces)
        # TODO: Add ranking based on how many cards are the same suit as Aces (Aces are more valuable if they are the only card of their suit) (AK is also valuable though so should not be penalized)
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down
        aces_sum = 0
        for playedCard in hand:
            if playedCard.card.rank == "A" and playedCard.card.suit != trump_suit:
                if playedCard.card.suit == playedCard.card.next_suit():
                    # Aces of the "next" suit are less valuable because there are less cards in that suit
                    aces_sum += 0.9
                else:
                    aces_sum += 1
        return aces_sum / 2.9 # Normalize value to 0-1 (max score is 2.9)

    def evaluate_voids(self, hand, trump_suit):
        """
        Evaluates the strength of the suit voids in the hand by counting the number of suits that are not in the hand and normalizing to 0-1
        """

        suits = set(playedCard.card.suit for playedCard in hand)

        if trump_suit not in suits:
            # If you don't have trump, voids are not valuable
            num_suits = 4
        else:
            num_suits = len(suits)

        return (4-num_suits) / 3 # Normalize value to 0-1 (max score is 3)

    def determine_random_card(self, hand, trump_suit, played_cards):
        """
        Determines a random card to play that is valid
        """
        if not played_cards:
            return hand[0]

        lead_suit = played_cards[0].card.suit
        valid_cards = [card for card in hand if card.card.suit == lead_suit]
        if valid_cards:
            return valid_cards[0]

        return hand[0]

    def determine_best_card(self, hand, trump_suit, played_cards, previous_cards, trump_caller):
        """
        Determines the best card to play in a trick
        """
        # TODO: Keep track of other players played cards - i.e. what trump are left

        # If you only have one card, play it
        if len(hand) == 1:
            return hand[0]

        partner_called_trump = trump_caller.team == self.team

        player_called_trump = trump_caller.name == self.name

        opponent_called_trump = trump_caller.team != self.team # TODO: It can be useful to know which opponent called trump specifically as that can change the card to play

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
        winning_card = max(played_cards, key=lambda pc: Card.euchre_rank(pc.card, trump_suit, lead_suit))
        current_winner = winning_card.player.name

        is_partner_winning = current_winner == self.partner
        player_is_last_to_play = len(played_cards) == 3

        # Gather cards by suit
        trump_cards = self.get_trump_cards(hand, trump_suit)
        if lead_suit == trump_suit:
            lead_suit_cards = trump_cards
        else:
            lead_suit_cards = [played_card for played_card in hand if played_card.card.suit == lead_suit and not played_card.card.is_left_bower(trump_suit)]

        # Get lowest card in hand
        lowest_card = min(hand, key=lambda x: Card.euchre_rank(x.card, trump_suit, lead_suit))

        if lead_suit_cards:
            high_lead = max(lead_suit_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit, lead_suit))
            low_lead = min(lead_suit_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit, lead_suit))

            # Follow suit
            if is_partner_winning:
                if player_is_last_to_play:
                    # Partner already has the trick won, so play lowest card
                    return low_lead
                elif self.is_boss_card(winning_card, previous_cards):
                    # If partner is winning with a boss card, play lowest card
                    return low_lead
                else:
                    # If partner is not winning with a boss card, play highest card if you can win trick
                    if high_lead.card.rank > winning_card.card.rank:
                        return high_lead
            else:
                # Opponent is winning, so play highest card if you can win trick
                if high_lead.card.rank > winning_card.card.rank:
                    return high_lead

            return low_lead

        played_trump_cards = self.get_trump_cards(played_cards, trump_suit)

        if not played_trump_cards:
            if trump_cards:
                small_trump = min(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))
                if is_partner_winning:
                    if player_is_last_to_play:
                        return lowest_card
                    elif not self.is_boss_card(winning_card, previous_cards):
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
        if trump_cards:
            if is_partner_winning:
                # Partner is winning with a trump card
                return lowest_card
            else:
                # Opponent is winning with a trump card
                winning_trump_cards = [card for card in trump_cards
                                    if Card.euchre_rank(card.card, trump_suit) > Card.euchre_rank(winning_card.card, trump_suit)]
                if winning_trump_cards:
                    # Play the highest trump necessary to take the lead
                    return min(winning_trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))
        # Cannot win trick, so play lowest card # TODO: making a void could be more valuable than playing lowest card (dealer_discard?)
        return lowest_card

    def choose_lead_card(self, hand, trump_suit, previous_cards, partner_called_trump, player_called_trump, opponent_called_trump):
        """
        Determines the best card to lead with
        """
        trump_cards = self.get_trump_cards(hand, trump_suit)

        # Get all cards that are the highest card in the suit remaining
        boss_cards = self.get_boss_cards_in_hand(hand, trump_suit, previous_cards)


        # If you called trump and have highest trump, lead it
        if player_called_trump:
            have_highest_trump = self.has_boss_card(hand, trump_suit, previous_cards)
            if have_highest_trump:
                #print("Lead with Right Bower - Player has High Trump")
                return max(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))
            elif len(trump_cards) > 1:
                #print("Lead with Lower Trump - Player has Lower Trump")
                return min(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # Lead strong if partner called trump
        if partner_called_trump and trump_cards:
            #print("Lead with strong card - Partner called")
            return max(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # If opponents called, lead boss off suit if you have it or lead low
        if opponent_called_trump:
            if boss_cards:
                #print("Lead with High off-suit - opponent called")
                return max(boss_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))
            else:
                #print("Lead with Low off-suit - opponent called")
                return min(hand, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # Lead highest off suit if it is a boss card
        if boss_cards:
            non_trump_boss = [card for card in boss_cards if card.card.suit != trump_suit]
            if non_trump_boss:
                #print("Lead with High off-suit - No trump but High Off")
                return max(non_trump_boss, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # Otherwise, simply lead lowest card
        #print("Lead with Low off-suit")
        return min(hand, key=lambda x: Card.euchre_rank(x.card, trump_suit))

    def get_boss_cards_in_hand(self, hand, trump_suit, previous_cards):
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
            temp_card = Card("J", suit)
            # Deal with bowers
            if not any(played_card.card.is_right_bower(suit) for played_card in previous_cards):
                return temp_card
            elif not any(played_card.card.is_left_bower(suit) for played_card in previous_cards):
                return Card("J", temp_card.next_suit()) # should be next suit

            # Both bowers have been played already
            card_ranks.remove("J")

        # Get all previous cards of the relevant suit
        relevant_previous_cards = [card for card in previous_cards if card.card.suit == suit]

        for card in relevant_previous_cards:
            if card.card.rank in card_ranks:
                card_ranks.remove(card.card.rank)

        return Card(card_ranks[0], suit) if card_ranks else None

    def is_boss_card(self, card, previous_cards):
        """
        Determines if a card is the highest card of the highest rank remaining in the suit
        """
        highest_card = self.get_boss_card(card.card.suit, previous_cards)

        return card.card.rank == highest_card.rank and card.card.suit == highest_card.suit

    def has_boss_card(self, hand, suit, previous_cards):
        """
        Determines if the hand has a boss card in the given suit
        """
        highest_card = self.get_boss_card(suit, previous_cards)

        if not highest_card:
            return False

        return any(played_card.card.rank == highest_card.rank and played_card.card.suit == highest_card.suit for played_card in hand)

    def get_trump_cards(self, hand, trump_suit):
        return [card for card in hand if card.card.suit == trump_suit or card.card.is_left_bower(trump_suit)]

    def dealer_pickup(self, dealer_hand, up_card, trump_suit):
        """
        Dealer gets up card and discards card
        """

        #print(f"{dealer_hand}")
        # Dealer gets up card and discards card
        dealer_hand.append(up_card)


        # Discard lowest non-trump card for now # TODO: Improve discarding logic (making a void is more valuable than discarding a low card)

        card_to_discard = self.dealer_discard(dealer_hand, trump_suit)
        dealer_hand.remove(card_to_discard)
        return dealer_hand

    def dealer_discard(self, dealer_hand, trump_suit):
        """
        Choose a card to discard based on creating a suit void if possible
        """
        trump_cards = self.get_trump_cards(dealer_hand, trump_suit)
        non_trump_cards = [card for card in dealer_hand if card not in trump_cards]

        if not non_trump_cards:
            # Hand is all trump cards, so discard lowest trump card
            return min(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # Find a possible void
        suit_counts = {}
        for card in non_trump_cards:
            suit = card.card.suit
            if suit not in suit_counts:
                suit_counts[suit] = []
            suit_counts[suit].append(card)

        # Find any suits with only one card (not Aces)
        possible_voids = [
            cards[0] for suit, cards in suit_counts.items()
            if len(cards) == 1 and cards[0].card.rank != "A"
        ]

        if possible_voids:
            # Choose the lowest card of the possible voids
            return min(possible_voids, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # If no possible voids, discard lowest non-trump card
        return min(non_trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))

class MonteCarloSimulation():
    def __init__(self):
        # Track number of calls and wins
        self.calls_round1 = {}
        self.calls_round2 = {}
        self.wins_round1 = {}
        self.wins_round2 = {}
        self.euchre_round1 = {}
        self.euchre_round2 = {}
        self.total_points = {}
        self.total_calls = {}
        self.total_wins = {}
        self.total_euchres = {}
        self.dealer_count = {}
        self.dealer_calls = {}
        self.dealer_points = {}
        self.player_card_stats = {}

        # Track team-level data
        self.team_calls = {1: 0, 2: 0}
        self.team_wins = {1: 0, 2: 0}
        self.team_euchres = {1: 0, 2: 0}
        self.team_points = {1: 0, 2: 0}
    def initialize_bots(self):
        bots = [
            Bot(name="Player", partner="Bot 3", team=1),
            Bot(name="Bot 2", partner="Bot 4", team=2),
            Bot(name="Bot 3", partner="Player", team=1),
            Bot(name="Bot 4", partner="Bot 2", team=2)
        ]
        # Initialize tracking
        for bot in bots:
            self.calls_round1[bot.name] = 0
            self.calls_round2[bot.name] = 0
            self.wins_round1[bot.name] = 0
            self.wins_round2[bot.name] = 0
            self.euchre_round1[bot.name] = 0
            self.euchre_round2[bot.name] = 0
            self.total_calls[bot.name] = 0
            self.total_wins[bot.name] = 0
            self.total_euchres[bot.name] = 0
            self.total_points[bot.name] = 0
            self.dealer_count[bot.name] = 0
            self.dealer_calls[bot.name] = 0
            self.dealer_points[bot.name] = 0

        return bots

    def run_simulation(self, num_simulations=1000):
        """
        Runs a simulation to determine the call percentage for each seat position in order to tweak thresholds and strategy weights
        """
        import random
        import time

        # Initialize Table
        Table.init_table()

        bots = self.initialize_bots()

        init_players = bots

        # Track number of wins for each team
        team1_wins = 0
        team2_wins = 0

        # Track number of calls for each team
        team1_calls = 0
        team2_calls = 0

        start_time = time.time()
        for game_num in range(num_simulations):
            # Make and shuffle deck

            # Track number of points for each team
            team1_points, team2_points = 0, 0

            random_dealer_index = random.randint(0, 3)
            players = []
            for player in init_players:
              players.append(init_players[(random_dealer_index + 1) % 4])
              random_dealer_index += 1

            # Track number of calls for each player
            calls_round1 = {player.name: 0 for player in players}
            calls_round2 = {player.name: 0 for player in players}

            num_total_rounds = 0

            # Simulate games
            while (team1_points < 10 and team2_points < 10):
              num_total_rounds += 1

              # Since we already have the dealer for the first round, we only
              # need to increment the index by 1 for each round
              if (team1_points != 0 or team2_points != 0):
                  random_dealer_index += 1
                  players = []
                  for player in init_players:
                    players.append(init_players[(random_dealer_index + 1) % 4])
                    random_dealer_index += 1

              # Dealer goes to last person the list, allowing the first person
              # to make the first decision
              dealer = players[3]
              self.dealer_count[dealer.name] += 1
              #print(f"Dealer is {dealer}")

              suits = ["hearts", "diamonds", "clubs", "spades"]
              ranks = ["A", "K", "Q", "J", "10", "9"]
              deck = [f"{rank} of {suit}" for rank in ranks for suit in suits]
              random.shuffle(deck)

              # Deal cards to players
              dealt_hands = {}
              for bot in players:
                  bot_cards = deck[:5]
                  deck = deck[5:]

                  dealt_hands[bot.name] = self.convert_to_played_cards(bot_cards, bot)
                  #print(f"{bot} hand is {bot_cards}")

              up_card_string = deck[0]
              #print(f"{up_card_string} is shown")

              up_card_rank, up_card_suit = up_card_string.split(" of ")
              up_card = PlayedCard(Card(up_card_rank, up_card_suit), dealer)

              # Each bot makes trump decision
              trump_maker = None
              for trump_round in (1, 2):
                  for bot in players:

                      decision = bot.determine_trump(
                          hand=dealt_hands[bot.name],
                          dealer=dealer,
                          up_card=up_card,
                          player_order=players,
                          trump_round=str(trump_round)
                      )

                      if decision != 'pass':
                          self.track_call_data(bot, trump_round, dealer)
                          trump_suit = decision
                          trump_maker = bot

                          #print(f"{trump_maker} calls {trump_suit}")

                          if trump_round == 1:
                              # Dealer gets up card and discards card
                              dealt_hands[dealer.name] = dealer.dealer_pickup(dealt_hands[dealer.name], up_card, decision)
                          break
                  if trump_maker:
                      break
                  #else:
                      #print("Everyone passes")

              # Use this to get stats on how many times each call was successful or euchred
              team1_p, team2_p = self.play_hand(game_num, team1_points, team2_points, dealt_hands, players, decision, trump_maker, up_card, dealer)

              team1_points += team1_p
              team2_points += team2_p
              self.track_results(trump_maker, team1_p, team2_p, trump_round, dealer)

            # Show results of each game
            #print(f"Game number {game_num + 1} Team 1 Score: {team1_points}, Team 2 Score: {team2_points}")
            if not game_num % 5:
                print (f'Game number: {game_num}/{num_simulations}')
                print(f'Time elapsed: {(time.time() - start_time)/60:.2f} min')

        #self.display_results(num_simulations)
        print (f'Games are complete')
        print(f'Total Time elapsed: {(time.time() - start_time)/60:.2f} min')

    def track_call_data(self, bot, trump_round, dealer):
        if trump_round == 1:
            self.calls_round1[bot.name] += 1
        else:
            self.calls_round2[bot.name] += 1
        self.total_calls[bot.name] += 1
        self.team_calls[bot.team] += 1

        if bot == dealer:
            self.dealer_calls[bot.name] += 1

    def track_results(self, trump_maker, team1_p, team2_p, trump_round, dealer):
        calling_team_won = (team1_p > team2_p and trump_maker.team == 1) or (team2_p > team1_p and trump_maker.team == 2)
        points_earned = team1_p if trump_maker.team == 1 else team2_p
        self.total_points[trump_maker.name] += team1_p if trump_maker.team == 1 else team2_p

        if trump_maker == dealer:
            self.dealer_points[trump_maker.name] += points_earned

        if calling_team_won:
            self.total_wins[trump_maker.name] += 1
            self.team_wins[trump_maker.team] += 1
            if trump_round == 1:
              self.wins_round1[trump_maker.name] += 1
            else:
              self.wins_round2[trump_maker.name] += 1
        else:
            self.total_euchres[trump_maker.name] += 1
            self.team_euchres[trump_maker.team] += 1

    def display_results(self, num_simulations):
        print("\n--- Results ---")
        print(f"Total Simulations: {num_simulations}")

        print("\nPlayer Card Win Probabilities:")
        for card, stats in self.player_card_stats.items():
            win_rate = stats['wins'] / stats['total'] if stats['total'] > 0 else 0
            print(f"{card}: {win_rate:.2f} ({stats['wins']}/{stats['total']})")

        for bot in self.total_calls.keys():
            print(f"\n{bot}:")
            print(f"  Total Calls: {self.total_calls[bot]}")
            print(f"  Total Wins: {self.total_wins[bot]}")
            print(f"  Total Euchres: {self.total_euchres[bot]}")
            print(f"  First Round Calls: {self.calls_round1[bot]} - Wins: {self.wins_round1[bot]}")
            print(f"  Second Round Calls: {self.calls_round2[bot]} - Wins: {self.wins_round2[bot]}")
            print(f"  Dealer Count: {self.dealer_count[bot]}")
            print(f"  Called Trump as Dealer: {self.dealer_calls[bot]}")

            # Calculate percentages
            win_rate = (self.total_wins[bot] / self.total_calls[bot]) * 100 if self.total_calls[bot] > 0 else 0
            first_round_rate = (self.wins_round1[bot] / self.calls_round1[bot]) * 100 if self.calls_round1[bot] > 0 else 0
            second_round_rate = (self.wins_round2[bot] / self.calls_round2[bot]) * 100 if self.calls_round2[bot] > 0 else 0
            euchre_rate = (self.total_euchres[bot] / self.total_calls[bot]) * 100 if self.total_calls[bot] > 0 else 0
            avg_points_per_call = self.total_points[bot] / self.total_calls[bot] if self.total_calls[bot] > 0 else 0
            call_trump_as_dealer = (self.dealer_calls[bot] / self.dealer_count[bot]) * 100 if self.dealer_count[bot] > 0 else 0
            avg_dealer_points = self.dealer_points[bot] / self.dealer_calls[bot]if self.dealer_calls[bot] > 0 else 0

            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  First Round Win Rate: {first_round_rate:.2f}%")
            print(f"  Second Round Win Rate: {second_round_rate:.2f}%")
            print(f"  Euchre Rate: {euchre_rate:.2f}%")
            print(f"  Avg Points Per Call: {avg_points_per_call:.2f}")
            print(f"  Call Trump as Dealer Rate: {call_trump_as_dealer:.2f}%")
            print(f"  Avg Points When Calling Trump as Dealer: {avg_dealer_points:.2f}")

        for team in (1, 2):
            print(f"\nTeam {team}:")
            print(f"  Total Calls: {self.team_calls[team]}")
            print(f"  Total Wins: {self.team_wins[team]}")
            print(f"  Total Euchres: {self.team_euchres[team]}")

    def play_hand(self, game_num, team1_points, team2_points, dealt_hands, players, trump_suit, trump_maker, up_card, dealer):
        """
        Plays a hand of Euchre
        """

        previous_cards = []
        team_tricks = [0, 0]

        # Create copy of players list to keep track of player order
        play_order = players[:]

        for trick_number in range(1, 6):
            # played cards for each trick
            played_cards = []

            # Each player plays a card
            for bot in play_order:
                # Evaluate player situation just before player has to play.
                card_to_play = bot.determine_best_card(dealt_hands[bot.name], trump_suit, played_cards, previous_cards, trump_maker)

                if(bot.name == "Player"):

                    # Perform montecarlo simulation for exploring each card in hard
                    card_probs = self.monte_carlo_card_evaluator( original_state={ "dealt_hands": dealt_hands, 
                                                                                  "previous_cards": previous_cards},
                                                                  player_hand=dealt_hands["Player"], play_order=players,
                                                                  trump_suit=trump_suit, trump_maker=trump_maker,
                                                                  num_simulations=25)

                    self.update_game_state(game_num, trick_number, team1_points, team2_points,
                        team_tricks, dealer, play_order, players, trump_maker, trump_suit, dealt_hands, 
                        card_to_play, up_card, previous_cards, card_probs)
                    
                    player_card_played = card_to_play.get_card()
                    player_team = bot.team

                dealt_hands[bot.name].remove(card_to_play)

                played_cards.append(card_to_play)

            # Determine the winner of the trick
            winner_name = self.evaluate_trick_winner(trump_suit, played_cards)
            winner = next((bot for bot in play_order if bot.name == winner_name), None)

            #print(f"{winner_name} won the round")

            # Add the played cards to the previous cards
            previous_cards.extend(played_cards)

            # Add 1 to the number of tricks the winner has in the original player list
            original_winner_index = players.index(winner)

            winning_team = winner.team

            # Team 1 points at index 0 and Team 2 points at index 1
            team_tricks[winning_team - 1] += 1


            #print(f"Team 1 tricks: {team_tricks[0]}, Team 2 tricks: {team_tricks[1]}")

            # Rotate the players list so that the winner leads the next trick
            winner_idx = play_order.index(winner)
            play_order = play_order[winner_idx:] + play_order[:winner_idx]

            team1_p, team2_p = self.evaluate_points(team_tricks[0], team_tricks[1], trump_maker)

            team1_points = team1_p
            team2_points = team2_p

        # Track result for players card
        if player_card_played:
            if player_card_played not in self.player_card_stats:
                self.player_card_stats[player_card_played] = {'wins': 0, 'total': 0}

            self.player_card_stats[player_card_played]['total'] += 1

            player_team_won = (team1_points > team2_points and player_team == 1) or (team2_points > team1_points and player_team == 2)
            if player_team_won:
                self.player_card_stats[player_card_played]['wins'] += 1

        return team1_points, team2_points

    def evaluate_trick_winner(self, trump_suit, played_cards):
        """
        Evaluates the winner of the trick
        """
        # Get the lead suit
        lead_suit = played_cards[0].card.suit

        winning_card = max(played_cards, key=lambda pc: Card.euchre_rank(pc.card, trump_suit, lead_suit))

        return winning_card.player.name

    def evaluate_points(self, team1_tricks, team2_tricks, trump_maker):
        """
        Evaluates the points for each team based on how many tricks they took
        """
        # 1 point if you call it and win 3 tricks
        # 2 points if you call it and win 5 tricks
        # 2 points if the other team calls it and you win 3 tricks
        # TODO: Update for alone attempts when that is implemented

        team1_points = 0
        team2_points = 0

        if trump_maker.team == 1:
            trump_calling_team = 1
        else:
            trump_calling_team = 2

        if team1_tricks >= 3:
            if trump_calling_team == 1:
                # Team 1 called trump and won
                team1_points += 1 if team1_tricks < 5 else 2
            else:
                # Team 1 euchred the other team
                team1_points += 2
        if team2_tricks >= 3:
            if trump_calling_team == 2:
                # Team 2 called trump and won
                team2_points += 1 if team2_tricks < 5 else 2
            else:
                # Team 2 euchred the other team
                team2_points += 2

        #print(f"Team 1: {team1_points}, Team 2: {team2_points}\n")

        return team1_points, team2_points

    def convert_to_played_cards(self, string_cards, player):
        dummy_hand = []
        for card_str in string_cards:
            rank, suit = card_str.split(" of ")
            dummy_card = Card(rank=rank, suit=suit)
            played_card = PlayedCard(card=dummy_card, player=player)
            dummy_hand.append(played_card)
        return dummy_hand

    def update_game_state(self, game_num, trick_number, team1_points, team2_points,
                      team_tricks, dealer, play_order, players, trump_maker, trump_suit,
                      dealt_hands, best_card, up_card, previous_cards, card_probs):

      index = 0
      teammate_dealer = False
      player_hand = []
      player = None

      for bot in play_order:
          if bot.name == "Player":
              player = bot
              if dealer.team == bot.team:
                  teammate_dealer = True
              player_hand = dealt_hands[bot.name]
              break
          else:
              index += 1

      known_cards = [up_card.get_card()]
      known_cards.extend([card.get_card() for card in previous_cards])

      win_data = self.player_card_stats.get(best_card.get_card() , {"wins": 0, "total": 0})
      win_prob = win_data["wins"] / win_data["total"] if win_data["total"] > 0 else 0

      # Generate one row per card in the hand
      for card in player_hand:
          card_str = card.get_card()

          game_state = {
              "game_id": game_num,
              "round_id": trick_number,
              "team1_score": team1_points,
              "team2_score": team2_points,
              "team1_round_score": team_tricks[0],
              "team2_round_score": team_tricks[1],
              "seat_position": index,
              "is_dealer": dealer.name == "Player",
              "partner_is_dealer": teammate_dealer,
              "trump_suit": trump_suit,
              "hand": [c.get_card() for c in player_hand],
              "known_cards": known_cards,
              "card_to_evaluate": card_str,
              "card_to_play": 1 if card.card == best_card.card else 0,
              "win_probability": card_probs[card.get_card()]
          }

          Table.update_table(game_state)  # Update table with each card as a row

      return  # You no longer return a single game_state, as you log multiple rows

    def monte_carlo_card_evaluator(self, original_state, player_hand, play_order, trump_suit, trump_maker, num_simulations=50):
        """
        Simulates N games for each card in the player's hand to estimate win probability.
        """
        import copy
        from collections import defaultdict

        card_win_stats = defaultdict(lambda: {'wins': 0, 'total': 0})
        player_team = [bot for bot in play_order if bot.name == "Player"][0].team

        for card in player_hand:
            card_str = card.get_card()

            for _ in range(num_simulations):
                # Deep copy the game state so each sim is fresh
                sim_hands = copy.deepcopy(original_state["dealt_hands"])
                sim_players = copy.deepcopy(play_order)
                sim_previous_cards = copy.deepcopy(original_state["previous_cards"])

                # Force player to play this card first
                sim_hands["Player"] = [c for c in sim_hands["Player"] if c.get_card() != card.get_card()]
                trick = [card]

                # Let others play their card in this trick using minimal logic
                for bot in sim_players:
                    if bot.name == "Player":
                        continue

                    lead_suit = card.card.suit
                    hand = sim_hands[bot.name]
                    if not hand:
                        continue  # Skip if no cards left

                    card_to_play = bot.determine_best_card( sim_hands[bot.name],
                        trump_suit, trick, sim_previous_cards,
                        trump_maker)
                    
                    sim_hands[bot.name].remove(card_to_play)
                    trick.append(card_to_play)

                # Determine winner of trick 
                winner_name = self.evaluate_trick_winner(trump_suit, trick)
                winner = next(p for p in sim_players if p.name == winner_name)

                # Randomly simulate remaining tricks (or use further logic)
                team_tricks = [0, 0]
                winning_team = winner.team
                team_tricks[winning_team - 1] += 1

                # Simulate 4 more tricks with simplified logic
                for _ in range(4):
                    trick = []
                    for bot in sim_players:
                        hand = sim_hands[bot.name]
                        if hand:
                            card_to_play = bot.determine_best_card( sim_hands[bot.name],
                                trump_suit, trick, sim_previous_cards,
                                trump_maker)
                            
                            sim_hands[bot.name].remove(card_to_play)
                            trick.append(card_to_play)
                    if trick:
                        winner_name = self.evaluate_trick_winner(trump_suit, trick)
                        winner = next(p for p in sim_players if p.name == winner_name)
                        team_tricks[winner.team - 1] += 1

                # Evaluate points
                team1_points, team2_points = self.evaluate_points(team_tricks[0], team_tricks[1], trump_maker)

                # Record result
                player_won = (player_team == 1 and team1_points > team2_points) or \
                            (player_team == 2 and team2_points > team1_points)

                card_win_stats[card_str]["total"] += 1
                if player_won:
                    card_win_stats[card_str]["wins"] += 1

        # Compute final probabilities
        card_probabilities = {}
        for card, stats in card_win_stats.items():
            total = stats["total"]
            wins = stats["wins"]
            card_probabilities[card] = wins / total if total > 0 else 0

        return card_probabilities

# TEMPORARY DATA GENERATION 
#if __name__ == "__main__":
#    simulation = MonteCarloSimulation()
#    simulation.run_simulation(100)