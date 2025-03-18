class BotLogic:
    def __init__(self):
        self.strategy_weights = {
            'trump_cards': 0.5,
            'off_aces': 0.4,
            'num_suits': 0.1
            # 'seat_position': 0.2
        }

    def determine_trump_test(self, player_name, hand, dealer, up_card, player_order, trump_round):
        """
        Determines trump by a very very simple scoring strategy
        """
        
        up_card_rank, trump_suit = up_card.split(" of ")
        position = self.get_seat_position(player_name, player_order)
        
        if position == 'first':
            position_bonus = 10
        elif position == 'third':
            position_bonus = 5
        else:
            position_bonus = 0

        if trump_round == "1":
            # First round
            trump_sum = self.get_hand_score(hand, trump_suit)

            if trump_sum + position_bonus >= 21:
                return trump_suit

        if trump_round == "2":
            # Second round
            # Same thing as round 1 except have to choose any remaining suit
            suits = ["hearts", "diamonds", "clubs", "spades"]
            suit_choices = [suit for suit in suits if suit != trump_suit]

            for suit in suit_choices:
                trump_sum = self.get_hand_score(hand, suit)

                if trump_sum >= 16:
                    return suit


            if player_name == dealer.name:
                # Dealer has to choose suit
                # Choose the suit that you have the most of
                suit_counts = {}
                for playedCard in hand:
                    if playedCard.card.suit != trump_suit:
                        if playedCard.card.suit not in suit_counts:
                            suit_counts[playedCard.card.suit] = 1
                        else:
                            suit_counts[playedCard.card.suit] += 1
                max_suit = max(suit_counts, key=suit_counts.get)
                return max_suit
            
        return 'pass'
            
    def get_hand_score(self, hand, trump_suit):
        """
        Gets the score of the hand based on the trump suit
        """
        left_bower_suit = self.get_next_suit(trump_suit)
        trump_sum = 0
        for playedCard in hand:
            if playedCard.card.rank == "J" and playedCard.card.suit == trump_suit:
                trump_sum += 10
            elif playedCard.card.rank == "J" and playedCard.card.suit == left_bower_suit:
                trump_sum += 7
            elif playedCard.card.suit == trump_suit:
                trump_ranks = {"A": 6, "K": 5, "Q": 4, "10": 4, "9": 4}
                trump_sum += trump_ranks[playedCard.card.rank]
            elif playedCard.card.suit != left_bower_suit:
                if playedCard.card.rank == "A":
                    trump_sum += 5
                elif playedCard.card.rank == "K":
                    trump_sum += 1
            elif playedCard.card.suit == left_bower_suit:
                if playedCard.card.rank == "A":
                    trump_sum += 4
                elif playedCard.card.rank == "K":
                    trump_sum += 1

        return trump_sum

    def determine_trump(self, player_name, hand, dealer, up_card, player_order, trump_round):
        """
        Determines the trump suit by scoring their hand and comparing it to the thresholds for their position
        """
        # TODO: Add taking into account the up card rank and who it is going to (maybe would just affect the position thresholds? Like if it is a bower, dealer position threshold goes wayyyyy down)

        # print("trump_round: ", trump_round)
        # print("player_name: ", player_name)
        # print(", ".join(str(playedCard) for playedCard in hand))
        # print("up_card: ", up_card)
        
        up_card_rank, trump_suit = up_card.split(" of ")
        position = self.get_seat_position(player_name, player_order)

        if trump_round == "1":
            # If you are dealer, in the first round, your hand should contain the up card and discard a card
            if player_name == dealer.name:
                temp_hand = hand.copy()
                up_card_rank, up_card_suit = up_card.split(" of ")
                up_card_played_card = PlayedCard(Card(up_card_rank, up_card_suit), dealer)
                temp_hand.append(up_card_played_card)
                # Discard lowest non-trump card for now # TODO: Improve discarding logic (making a void is more valuable than discarding a low card)
                trump_cards = self.get_trump_cards(temp_hand, trump_suit)
                non_trump_cards = [card for card in temp_hand if card not in trump_cards]
                if non_trump_cards:
                    card_to_discard = min(non_trump_cards, key=lambda x: x.card.rank)
                else:
                    # If you only have trump cards, discard lowest trump card
                    card_to_discard = min(temp_hand, key=lambda x: x.card.rank)
                temp_hand.remove(card_to_discard)

                hand_score = self.evaluate_hand(temp_hand, trump_suit)
            else:
                hand_score = self.evaluate_hand(hand, trump_suit)
            # print("hand_score: ", hand_score)

            first_round_position_thresholds = {
                'first': 0.42,
                'second': 0.35,
                'third': 0.44,
                'dealer': 0.35
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
        """
        Returns the position of the player in the player order
        """
        positions = ['first', 'second', 'third', 'dealer']

        for i, player in enumerate(player_order):
            if player['name'] == player_name:
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

        return trump_sum / 4 # Normalize value to 0-1 (max score is 4)

    def evaluate_aces(self, hand, trump_suit):
        """
        Evaluates the strength of the aces in the hand by adding 1 per ace and normalizing to 0-1
        """
        # TODO: Add evaluation for doubletons (Kx, Qx) as those should be evaluated differently (could become sorta like aces)
        # TODO: Add ranking based on how many cards are the same suit as Aces (Aces are more valuable if they are the only card of their suit) (AK is also valuable though so should not be penalized)
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down
        left_bower_suit = self.get_next_suit(trump_suit)
        aces_sum = 0
        for playedCard in hand:
            if playedCard.card.rank == "A" and playedCard.card.suit != trump_suit:
                if playedCard.card.suit == left_bower_suit:
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

    def determine_best_card_new(self, hand, trump_suit, played_cards, previous_cards, trump_caller, num_tricks_team, num_tricks_opponent):
        # Check if you are leading
        if not played_cards:
            # Decide what card to lead
            return self.choose_lead_card(hand, trump_suit, previous_cards, trump_caller, num_tricks_team, num_tricks_opponent)
        
        # Not leading, so get suit that was lead
        lead_suit = played_cards[0].card.suit
        left_bower_suit = self.get_next_suit(trump_suit)

        # Find winner of current trick
        winning_card = max(played_cards, key=lambda pc: self.euchre_rank(pc.card, trump_suit, left_bower_suit, lead_suit))
        current_winner = winning_card.player.name

        # Gather cards by suit
        trump_cards = self.get_trump_cards(hand, trump_suit)
        lead_suit_cards = [played_card for played_card in hand if played_card.card.suit == lead_suit]

        is_partner_winning = current_winner == self.get_partner()
            
            

    def determine_best_card(self, hand, trump_suit, played_cards):
        """
        Determines the best card to play in a trick
        """
        # TODO: See what partner has played (if they are winning trick, don't take it)
        # TODO: If you are the last player, you know what you need to take the trick

        trump_cards = self.get_trump_cards(hand, trump_suit)

        if len(played_cards) == 0:
            # Decide what card to lead
            # TODO: Depends on who called trump and so many other factors
            # TODO: play could depend on what was played in previous tricks
            # TODO: If there is a tie of the highest card (such as two Aces), next Ace is usually worse
            # For now, simply play highest card
            return max(hand, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))

        else:
            # Decide what card to play
            
            # Get the lead suit
            lead_suit = played_cards[0].card.suit

            # Get the cards of the lead suit
            lead_suit_cards = [card for card in hand if card.card.suit == lead_suit]

            if len(lead_suit_cards) != 0:
                # Follow suit
                # If you have the highest card (like Ace or Right Bower) of the lead suit, play it
                # TODO: have to keep track of what cards have been played, so cannot hardcode highest cards because eventually highest card will be different (If the right bower is played, then the left bower is the highest card)
                if lead_suit == trump_suit:
                    # Play right if you have it, otherwise play low
                    if "J" in [card.card.rank for card in lead_suit_cards]:
                        max(lead_suit_cards, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))
                elif "A" in [card.card.rank for card in lead_suit_cards]:
                    return max(lead_suit_cards, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))
                # Otherwise, play the lowest card of the lead suit
                return min(lead_suit_cards, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))
            else:
                # If you don't have any cards of the lead suit, can either trump in or throw off
                if len(trump_cards) != 0:
                    # Trump in if you can take it (higher trump than any trump in played card)
                    # TODO: Don't overtrump your partner
                    played_trump_cards = self.get_trump_cards(played_cards, trump_suit)
                    if not played_trump_cards or max(trump_cards, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit))).card.rank > max(played_trump_cards, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit))).card.rank:
                        return max(trump_cards, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))
                    else:
                        # Otherwise, throw off
                        return min(hand, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))
                else:
                    # If you don't have any trump cards, throw off
                    return min(hand, key=lambda x: self.euchre_rank(x.card, trump_suit, self.get_next_suit(trump_suit)))
                
    def get_trump_cards(self, hand, trump_suit):
        left_bower_suit = self.get_next_suit(trump_suit)
        return [card for card in hand if card.card.suit == trump_suit or (card.card.suit == left_bower_suit and card.card.rank == "J")]
         

    def get_next_suit(self, suit):
        """Returns the other suit of the same color as suit"""
        suits_pairs = {
            'hearts': 'diamonds',
            'diamonds': 'hearts',
            'clubs': 'spades',
            'spades': 'clubs'
        }
        return suits_pairs[suit]

    def euchre_rank(self, card, trump_suit, left_bower_suit, lead_suit=None):
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

class MonteCarloSimulation(BotLogic):
    def run_simulation(self, num_simulations=1000):
        """
        Runs a simulation to determine the call percentage for each seat position in order to tweak thresholds and strategy weights
        """
        import random
        
        players = [
            {"name": "Bot 1"},
            {"name": "Bot 2"},
            {"name": "Bot 3"},
            {"name": "Bot 4"} # always dealer
        ]
        team1 = [players[0]['name'], players[2]['name']]
        team2 = [players[1]['name'], players[3]['name']]

        # dealer = random.choice(players)
        # player_order = [player for player in players if player != dealer]

        calls_round1 = {player['name']: 0 for player in players}
        calls_round2 = {player['name']: 0 for player in players}

        team1_points, team2_points = 0, 0
        team1_wins = 0
        team2_wins = 0
        team1_calls = 0
        team2_calls = 0

        for _ in range(num_simulations):
            # Make and shuffle deck
            suits = ["hearts", "diamonds", "clubs", "spades"]
            ranks = ["A", "K", "Q", "J", "10", "9"]
            deck = [f"{rank} of {suit}" for rank in ranks for suit in suits]
            random.shuffle(deck)


            # Convert players list to a list of dummy players
            dummy_players = [Player(name=player['name']) for player in players]

            # Deal cards to players
            dealt_hands = {}
            for bot in players:
                bot_cards = deck[:5]
                deck = deck[5:]

                dealt_hands[bot['name']] = self.convert_to_played_cards(bot_cards, dummy_players[players.index(bot)])

            up_card = deck[0]

            # Each bot makes trump decision
            for trump_round in range(1, 3):
                trump_called = False
                for bot in players:

                    decision = self.determine_trump(
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

                            # Dealer gets up card and discards card
                            dealer_hand = dealt_hands[dummy_players[3].name]
                            up_card_rank, up_card_suit = up_card.split(" of ")
                            up_card_played_card = PlayedCard(Card(up_card_rank, up_card_suit), dummy_players[3])
                            dealer_hand.append(up_card_played_card)

                            # Discard lowest non-trump card for now # TODO: Improve discarding logic (making a void is more valuable than discarding a low card)
                            non_trump_cards = [card for card in dealer_hand if card.card.suit != decision]
                            if non_trump_cards:
                                card_to_discard = min(non_trump_cards, key=lambda x: x.card.rank)
                            else:
                                # If you only have trump cards, discard lowest trump card
                                card_to_discard = min(dealer_hand, key=lambda x: x.card.rank)
                            dealer_hand.remove(card_to_discard)
                            dealt_hands[dummy_players[3].name] = dealer_hand
                        else:
                            calls_round2[bot['name']] += 1
                        trump_called = True
                        trump_maker = bot['name']
                        break

                    # print(f"{bot['name']} called trump: {decision}")

                if trump_called:
                    break

            # Use this to get stats on how many times each call was successful or euchred
            team1_points, team2_points = self.play_hand(dealt_hands, players, decision, trump_maker, team1)

            # Calculate calls and wins
            if trump_maker in team1:
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

    def play_hand(self, dealt_hands, players, trump_suit, trump_maker, team1):
        """
        Plays a hand of Euchre
        """

        tricks_data = []
        seat_tricks = [0, 0, 0, 0]
        leader_seat = 0

        play_order = players.copy()

        for trick_number in range(1, 6):
            played_cards = []
            for bot in play_order:
                card_to_play = self.determine_random_card(dealt_hands[bot['name']], trump_suit, played_cards)
                played_cards.append(card_to_play)

            # Determine the winner of the trick
            winner = self.evaluate_trick_winner(trump_suit, played_cards)
            local_winner_index = play_order.index({'name': winner})

            original_winner_index = next(
                i for i, player in enumerate(players) if player['name'] == winner
            )
            seat_tricks[original_winner_index] += 1

            ## Add result to tricks_data
            tricks_data.append({
                'trick_number': trick_number,
                'winner': winner
            })

            # Rearrange the players list so that the leader is first
            play_order = play_order[local_winner_index:] + play_order[:local_winner_index]

        # Calculate the points for each team
        team1_tricks = seat_tricks[0] + seat_tricks[2]
        team2_tricks = seat_tricks[1] + seat_tricks[3]

        return self.evaluate_points(team1_tricks, team2_tricks, trump_maker, team1)

    def evaluate_trick_winner(self, trump_suit, played_cards):
        """
        Evaluates the winner of the trick
        """
        # Get the lead suit
        lead_suit = played_cards[0].card.suit
        left_bower_suit = self.get_next_suit(trump_suit)
        
        winning_card = max(played_cards, key=lambda pc: self.euchre_rank(pc.card, trump_suit, left_bower_suit, lead_suit))

        # print  out played cards to see if it is working
        # print(f"Played cards: {[card.player.name + ': ' + card.card.rank + ' of ' + card.card.suit for card in played_cards]}")
        # print(f"Winning card: {winning_card.player.name}")
        return winning_card.player.name

    def evaluate_points(self, team1_tricks, team2_tricks, trump_maker, team1):
        """
        Evaluates the points for each team based on how many tricks they took
        """
        # 1 point if you call it and win 3 tricks
        # 2 points if you call it and win 5 tricks
        # 2 points if the other team calls it and you win 3 tricks
        # TODO: Update for alone attempts when that is implemented

        team1_points = 0
        team2_points = 0

        if trump_maker in team1:
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
                
class Player():
    def __init__(self, name, is_human=False, partner, team):
        self.name = name
        self.is_human = is_human
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

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank} of {self.suit}"


class PlayedCard():
    def __init__(self, card, player):
        self.player = player
        self.card = card

    def __str__(self):
        return f"{self.player.name} played {self.card.rank} of {self.card.suit}"

        
if __name__ == "__main__":
    simulation = MonteCarloSimulation()
    simulation.run_simulation(1000000)