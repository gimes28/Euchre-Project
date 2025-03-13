class BotLogic:
    def __init__(self):
        self.strategy_weights = {
            'trump_cards': 0.5,
            'off_aces': 0.4,
            'num_suits': 0.1
            # 'seat_position': 0.2
        }

    def determine_trump(self, player_name, hand, dealer, up_card, player_order, trump_round):
        # Returns the suit that the bot should call as trump or if the bot should pass
        """
        Implementing specific strategies for calling trump in Euchre

        Things to consider:
        - How many trump cards are in the hand
            - And specifically the strength of the trump cards as well (right bower, left bower, etc.)
        - How many suits we have (any voids?)
        - Seat position! (1st, 2nd, 3rd, 4th) 
        - Who the dealer is (who is going to get the upcard)
        - What the upcard is (if it's a strong card, we might want to pass)
        (1st is left of dealer, 2nd is across, 3rd is right of dealer, 4th is dealer)
            - 3rd seat is hardest to order from (need very strong hand)
            - 4th (dealer) is easiest (you gain extra trump and everyone has already passed)
            - 2nd can order with a weaker hand because partner is getting a trump
            - 1st seat is difficult in first round; however, you get the lead, making it much better than 3rd seat
            - 1st seat is really good for second round calls (Next strategy) and also for tricking the other team into calling it up in the first round
        - Score of the game (if we're winning, can take less risks, if losing, more risks)
        - Donations...?

        ISSUES:
        - HAVE TO CONSIDER LEFT BOWER AS WELL
        - Need way to check if you are dealer AND if teammate is dealer.
        - Need way to get seat number (should be easy enough to figure out once this is connected to the game)
        - Implement a doubleton as ace (Kx, maybe Qx)
        - Second round, dealer cannot pass
        - Reverse next for 2nd and maybe dealer, next for 1st and maybe 3rd.

        """

        print("player_name: ", player_name)
        print("hand: ", hand)
        print("dealer: ", dealer)
        print("up_card: ", up_card)
        print("trump_round: ", trump_round)
        print("player_order: ", player_order)

        if trump_round == "1":
            # First round
            up_card_rank, trump_suit = up_card.split(" of ")
            left_bower_suit = self.get_next_suit(trump_suit)
            print("left_bower_suit: ", left_bower_suit)
            trump_cards = [playedCard for playedCard in hand if (playedCard.card.suit == trump_suit) or (playedCard.card.rank == "J" and playedCard.card.suit == left_bower_suit)]
            num_trump_cards = len(trump_cards)

            print("trump_cards: ", trump_cards)
            print("num_trump_cards: ", num_trump_cards)

            num_aces = len([playedCard for playedCard in hand if (playedCard.card.rank == "A" and playedCard.card.suit != trump_suit)])

            print("num_aces: ", num_aces)
            
            if num_trump_cards + num_aces >= 4:
                # ORDER UP (4 trumps is automatic order up and aces are almost as valuable as trumps)
                print("ORDER UP - 4 trumps or 3 trumps and an ace")
                return trump_suit

            # Count number of suits
            suits = []
            for playedCard in hand:
                if playedCard.card.suit not in suits:
                    suits.append(playedCard.card.suit)
            num_suits = len(suits)

            if (num_trump_cards >= 3 and num_suits <= 2):
                # ORDER UP (3 trump 2 suited is automatic order up)
                print("ORDER UP - 3 trumps and 2 suited")
                return trump_suit

        if trump_round == "2":
            # Second round
            # Bot can now choose any suit other than the up card suit as trump
            # This means that the bot can choose the suit that they have the most of a combination of trump and aces 
            up_card_rank, up_card_suit = up_card.split(" of ")
            suits = []
            for playedCard in hand:
                if playedCard.card.suit not in suits:
                    suits.append(playedCard.card.suit)
            num_suits = len(suits)

            # Dealer has to choose suit
            if player_name == dealer.name:
                # Dealer has to choose suit
                # Choose the suit that you have the most of
                suit_counts = {}
                for playedCard in hand:
                    if playedCard.card.suit != up_card_suit:
                        if playedCard.card.suit not in suit_counts:
                            suit_counts[playedCard.card.suit] = 1
                        else:
                            suit_counts[playedCard.card.suit] += 1
                print("suit_counts: ", suit_counts)
                max_suit = max(suit_counts, key=suit_counts.get)
                print("max_suit: ", max_suit)
                return max_suit

        return 'pass' # Hand not strong enough to call trump

    def determine_trump_by_ranking(self, player_name, hand, dealer, up_card, player_order, trump_round):
        # TODO: Add taking into account the up card rank and who it is going to (maybe would just affect the position thresholds? Like if it is a bower, dealer position threshold goes wayyyyy down)

        # readable_hand = [f"{playedCard.card.rank} of {playedCard.card.suit}" for playedCard in hand]
        # print("trump_round: ", trump_round)
        # print("player_name: ", player_name)
        # print("hand: ", readable_hand)
        # print("up_card: ", up_card)
        
        up_card_rank, trump_suit = up_card.split(" of ")
        position = self.get_seat_position(player_name, player_order)

        if trump_round == "1":
            hand_score = self.evaluate_hand(hand, trump_suit)
            # print("hand_score: ", hand_score)

            first_round_position_thresholds = {
                'first': 0.42,
                'second': 0.35,
                'third': 0.45,
                'dealer': 0.275
            }

            threshold = first_round_position_thresholds[position]
    
            # print("position: ", position)
            # print("threshold: ", threshold)
            
            return trump_suit if hand_score >= threshold else 'pass'
        
        if trump_round == "2":
            second_round_thresholds = {
                'first': {
                    'next': 0.275,
                    'reverse': 0.4
                },
                'second': {
                    'next': 0.4,
                    'reverse': 0.275
                },
                'third': {
                    'next': 0.25,
                    'reverse': 0.35
                },
                'dealer': {
                    'next': 0.35,
                    'reverse': 0.25
                }
            }

            next_suit = self.get_next_suit(trump_suit)

            suits = ["hearts", "diamonds", "clubs", "spades"]
            reverse_suits = [suit for suit in suits if suit not in [trump_suit, next_suit]]

            seat_thresholds = second_round_thresholds[position]

            next_suit_score = self.evaluate_hand(hand, next_suit)
            if next_suit_score >= seat_thresholds['next']:
                # print("NEXT SUIT - ", next_suit)
                # print("NEXT SUIT SCORE - ", next_suit_score)
                return next_suit
            
            reverse_suit_score_1 = self.evaluate_hand(hand, reverse_suits[0])
            reverse_suit_score_2 = self.evaluate_hand(hand, reverse_suits[1])
            
            if reverse_suit_score_1 >= seat_thresholds['reverse'] or reverse_suit_score_2 >= seat_thresholds['reverse']:
                # print("REVERSE SUIT - ", reverse_suits[0] if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suits[1])
                # print("REVERSE SUIT SCORE - ", reverse_suit_score_1 if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suit_score_2)
                return reverse_suits[0] if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suits[1]
            
            if player_name == dealer.name:
                options = [
                    (next_suit, next_suit_score),
                    (reverse_suits[0], reverse_suit_score_1),
                    (reverse_suits[1], reverse_suit_score_2)
                ]

                best_suit, _ = max(options, key=lambda x: x[1])
                return best_suit

            return 'pass'
        
    def get_seat_position(self, player_name, player_order):
        positions = ['first', 'second', 'third', 'dealer']

        for i, player in enumerate(player_order):
            if player['name'] == player_name:
                return positions[i]

    def evaluate_hand(self, hand, trump_suit):
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
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down, so should be evaluated differently
        # TODO: Dealer should be evaluated differently: you pick up the up card and discard so hand should evaluated differently

        left_bower_suit = self.get_next_suit(trump_suit)
        trump_sum = 0

        for playedCard in hand:
            if playedCard.card.rank == "J" and playedCard.card.suit == trump_suit:
                trump_sum += 1
            elif playedCard.card.rank == "J" and playedCard.card.suit == left_bower_suit:
                trump_sum += 0.9
            elif playedCard.card.suit == trump_suit:
                trump_ranks = {"A": 0.8, "K": 0.7, "Q": 0.6, "10": 0.5, "9": 0.4}
                trump_sum += trump_ranks[playedCard.card.rank]

        return trump_sum / 4 # Normalize value to 0-1

    def evaluate_aces(self, hand, trump_suit):
        # TODO: Add evaluation for doubletons (Kx, Qx) as those should be evaluated differently (could become sorta like aces)
        # TODO: Add ranking based on how many cards are the same suit as Aces (Aces are more valuable if they are the only card of their suit) (AK is also valuable though so should not be penalized)
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down
        left_bower_suit = self.get_next_suit(trump_suit)
        aces_sum = 0
        for playedCard in hand:
            if playedCard.card.rank == "A" and playedCard.card.suit != trump_suit:
                if playedCard.card.suit == left_bower_suit:
                    aces_sum += 0.9
                else:
                    aces_sum += 1
        return aces_sum / 2.9 # Normalize value to 0-1

    def evaluate_voids(self, hand, trump_suit):
        # TODO: voids are really only useful if you have trump, otherwise they are not valuable

        suits = set(playedCard.card.suit for playedCard in hand)

        if trump_suit not in suits:
            num_suits = 4
        else:
            num_suits = len(suits)
        
        return (4-num_suits) / 3 # Normalize value to 0-1

    def determine_best_card(self, hand, trump_suit, played_cards):
        # Returns the card that the bot should play
        
        pass 

    def get_next_suit(self, trump_suit):
        """Returns the other suit of the same color"""
        suits_pairs = {
            'hearts': 'diamonds',
            'diamonds': 'hearts',
            'clubs': 'spades',
            'spades': 'clubs'
        }
        return suits_pairs[trump_suit]

class MonteCarloSimulation(BotLogic):
    def run_simulation(self, num_simulations=1000):
        import random
        
        players = [
            {"name": "Bot 1"},
            {"name": "Bot 2"},
            {"name": "Bot 3"},
            {"name": "Bot 4"} # always dealer
        ]

        # dealer = random.choice(players)
        # player_order = [player for player in players if player != dealer]

        calls_round1 = {player['name']: 0 for player in players}
        calls_round2 = {player['name']: 0 for player in players}

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

                dealt_hands[bot['name']] = self.convert_to_played_cards(bot_cards)

            up_card = deck[0]

            # Convert players list to a list of dummy players
            dummy_players = [type("DummyPlayer", (object,), {"name": player['name']}) for player in players]

            # Each bot makes trump decision
            for trump_round in range(1, 3):
                trump_called = False
                for bot in players:

                    decision = self.determine_trump_by_ranking(
                        player_name=bot['name'],
                        hand=dealt_hands[bot['name']],
                        dealer=dummy_players[3],
                        up_card=up_card,
                        player_order=players,
                        trump_round=str(trump_round)
                    )

                    if decision != 'pass':
                        if trump_round == 1:
                            calls_round1[bot['name']] += 1
                        else:
                            calls_round2[bot['name']] += 1
                        trump_called = True
                        break

                    # print(f"{bot['name']} called trump: {decision}")

                if trump_called:
                    break

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

        return total_call_rates
                
    def convert_to_played_cards(self, string_cards):
        dummy_hand = []
        for card_str in string_cards:
            rank, suit = card_str.split(" of ")
            dummy_card = type("DummyCard", (object,), {"rank": rank, "suit": suit})
            played_card = type("DummyPlayedCard", (object,), {"card": dummy_card})
            dummy_hand.append(played_card)
        return dummy_hand
        
if __name__ == "__main__":
    simulation = MonteCarloSimulation()
    simulation.run_simulation(10000)
                
