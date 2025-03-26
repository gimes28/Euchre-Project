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
        return f"{self.player.name} played {self.card.rank} of {self.card.suit}"
    
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

        partner_called_trump = trump_caller == self.partner
        player_called_trump = trump_caller == self.name
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

        # Lead strong if partner called trump
        if partner_called_trump and trump_cards:
            return max(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # If you called trump and have highest trump, lead it
        if player_called_trump:
            have_highest_trump = self.has_boss_card(hand, trump_suit, previous_cards)
            if have_highest_trump:
                return max(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))
            elif len(trump_cards) > 1:
                return min(trump_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # If opponents called, lead boss off suit if you have it or lead low
        if opponent_called_trump:
            if boss_cards:
                return max(boss_cards, key=lambda x: Card.euchre_rank(x.card, trump_suit))
            else:
                return min(hand, key=lambda x: Card.euchre_rank(x.card, trump_suit))
            
        # Lead highest off suit if it is a boss card
        if boss_cards:
            non_trump_boss = [card for card in boss_cards if card.card.suit != trump_suit]
            if non_trump_boss:
                return max(non_trump_boss, key=lambda x: Card.euchre_rank(x.card, trump_suit))

        # Otherwise, simply lead lowest card
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
    def run_simulation(self, num_simulations=1000):
        """
        Runs a simulation to determine the call percentage for each seat position in order to tweak thresholds and strategy weights
        """
        import random

        bot1 = Bot("Bot 1", partner="Bot 3", team=1)
        bot2 = Bot("Bot 2", partner="Bot 4", team=2)
        bot3 = Bot("Bot 3", partner="Bot 1", team=1)
        bot4 = Bot("Bot 4", partner="Bot 2", team=2) # always dealer

        players = [bot1, bot2, bot3, bot4]

        # team1 = [players[0]['name'], players[2]['name']]
        # team2 = [players[1]['name'], players[3]['name']]

        # dealer = random.choice(players)
        # player_order = [player for player in players if player != dealer]

        # Track number of calls for each player
        calls_round1 = {player.name: 0 for player in players}
        calls_round2 = {player.name: 0 for player in players}

        # Track number of wins for each team
        team1_points, team2_points = 0, 0
        team1_wins = 0
        team2_wins = 0

        # Track number of calls for each team
        team1_calls = 0
        team2_calls = 0

        for _ in range(num_simulations):
            # Make and shuffle deck
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

            up_card_string = deck[0]

            dealer = bot4
            
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
                        if trump_round == 1:
                            calls_round1[bot.name] += 1

                            # Dealer gets up card and discards card
                            dealt_hands[dealer.name] = dealer.dealer_pickup(dealt_hands[dealer.name], up_card, decision)
                        else:
                            calls_round2[bot.name] += 1
                        trump_maker = bot

                        break

                if trump_maker:
                    break

            # Use this to get stats on how many times each call was successful or euchred
            team1_points, team2_points = self.play_hand(dealt_hands, players, decision, trump_maker)

            # Calculate calls and wins
            if trump_maker.team == 1:
                team1_calls += 1
                if team1_points > team2_points:
                    team1_wins += 1
            else:
                team2_calls += 1
                if team2_points > team1_points:
                    team2_wins += 1

        # Calculate probabilities
        call_rates_round1 = {
            name: round(count / num_simulations * 100, 2)
            for name, count in calls_round1.items()
        }
        call_rates_round2 = {
            name: round(count / num_simulations * 100, 2)
            for name, count in calls_round2.items()
        }

        total_calls = {
            name: calls_round1[name] + calls_round2[name]
            for name in calls_round1
        }
        total_call_rates = {
            name: round(total_calls[name] / num_simulations * 100, 2)
            for name in calls_round1
        }

        print(f"Round 1 call rates after {num_simulations} simulations:")
        for name, rate in call_rates_round1.items():
            print(f"{name}: {rate}%")

        print(f"Round 2 call rates after {num_simulations} simulations:")
        for name, rate in call_rates_round2.items():
            print(f"{name}: {rate}%")

        print(f"Total call rates after {num_simulations} simulations:")
        for name, rate in total_call_rates.items():
            print(f"{name}: {rate}%")

        # Calculate win rates
        if team1_calls != 0:
            print(f"Team 1 wins: {team1_wins}")
            print(f"Team 1 calls: {team1_calls}")
            team1_win_rate = team1_wins / team1_calls
        else:
            team1_win_rate = 0
        if team2_calls != 0:
            print(f"Team 2 wins: {team2_wins}")
            print(f"Team 2 calls: {team2_calls}")
            team2_win_rate = team2_wins / team2_calls
        else:
            team2_win_rate = 0

        print(f"Team 1 win rate after {num_simulations} simulations: {team1_win_rate}")
        print(f"Team 2 win rate after {num_simulations} simulations: {team2_win_rate}")

    def play_hand(self, dealt_hands, players, trump_suit, trump_maker):
        """
        Plays a hand of Euchre
        """

        previous_cards = []
        seat_tricks = [0, 0, 0, 0]

        # Create copy of players list to keep track of player order
        play_order = players[:]

        for trick_number in range(1, 6):
            played_cards = []

            # Each player plays a card
            for bot in play_order:
                card_to_play = bot.determine_best_card(dealt_hands[bot.name], trump_suit, played_cards, previous_cards, trump_maker)

                dealt_hands[bot.name].remove(card_to_play)

                played_cards.append(card_to_play)

            # Determine the winner of the trick
            winner_name = self.evaluate_trick_winner(trump_suit, played_cards)
            winner = next((bot for bot in play_order if bot.name == winner_name), None)

            # Add the played cards to the previous cards
            previous_cards.extend(played_cards)

            # Add 1 to the number of tricks the winner has in the original player list
            original_winner_index = players.index(winner)
            seat_tricks[original_winner_index] += 1

            # Rotate the players list so that the winner leads the next trick
            winner_idx = play_order.index(winner)
            play_order = play_order[winner_idx:] + play_order[:winner_idx]

        # Calculate the points for each team
        team1_tricks = seat_tricks[0] + seat_tricks[2]
        team2_tricks = seat_tricks[1] + seat_tricks[3]

        return self.evaluate_points(team1_tricks, team2_tricks, trump_maker)

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

        return team1_points, team2_points

    def convert_to_played_cards(self, string_cards, player):
        dummy_hand = []
        for card_str in string_cards:
            rank, suit = card_str.split(" of ")
            dummy_card = Card(rank=rank, suit=suit)
            played_card = PlayedCard(card=dummy_card, player=player)
            dummy_hand.append(played_card)
        return dummy_hand        

        
if __name__ == "__main__":
    simulation = MonteCarloSimulation()
    simulation.run_simulation(10000)