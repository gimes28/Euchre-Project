from bot_logic import BotLogic

class Bot(BotLogic):
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
        return self.suit == self.SUITS_PAIRS[trump_suit] and self.rank == 'J'
    
class PlayedCard():
    def __init__(self, card, player):
        self.player = player
        self.card = card

    def __str__(self):
        return f"{self.player.name} played {self.card.rank} of {self.card.suit}"
    
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

        # Track number of calls for each player
        calls_round1 = {player.name: 0 for player in players}
        calls_round2 = {player.name: 0 for player in players}

        # Track number of wins for each team
        team1_wins = 0
        team2_wins = 0

        # Track number of calls for each team
        team1_calls = 0
        team2_calls = 0

        # Track number of times each team marches
        team1_marches = 0
        team2_marches = 0

        # Track total points for each team
        team1_total_points = 0
        team2_total_points = 0

        # Track loner attempts
        loner_attempts_round1 = {player.name: 0 for player in players}
        loner_attempts_round2 = {player.name: 0 for player in players}
        team1_loner_attempts = 0
        team2_loner_attempts = 0
        team1_loner_wins = 0
        team2_loner_wins = 0

        for _ in range(num_simulations):
            
            team1_points, team2_points = 0, 0

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

                dealt_hands[bot.name] = self.convert_to_cards(bot_cards, bot)

            up_card_string = deck[0]

            dealer = bot4
            
            up_card_rank, up_card_suit = up_card_string.split(" of ")
            up_card = Card(up_card_rank, up_card_suit)

            # Each bot makes trump decision
            trump_maker = None
            for trump_round in (1, 2):
                for bot in players:

                    trump_decision, going_alone = bot.determine_trump(
                        hand=dealt_hands[bot.name],
                        dealer=dealer,
                        up_card=up_card,
                        player_order=players,
                        trump_round=str(trump_round)
                    )

                    if trump_decision != 'pass':

                        # print(f"{bot.name} called {trump_decision} ({up_card}) in round {trump_round} with hand: {', '.join([str(card) for card in dealt_hands[bot.name]])} ({going_alone})")

                        if trump_round == 1:
                            calls_round1[bot.name] += 1

                            if going_alone:
                                loner_attempts_round1[bot.name] += 1

                            dealt_hands[dealer.name].append(up_card)
                            
                            discarded_card = dealer.get_worst_card(dealt_hands[dealer.name], up_card.suit)
                            dealt_hands[dealer.name].remove(discarded_card)
                        else:
                            calls_round2[bot.name] += 1

                            if going_alone:
                                loner_attempts_round2[bot.name] += 1

                        trump_maker = bot

                        break

                if trump_maker:
                    break

            # Use this to get stats on how many times each call was successful or euchred
            team1_points, team2_points = self.play_hand(dealt_hands, players, trump_decision, trump_maker, going_alone)

            team1_total_points += team1_points
            team2_total_points += team2_points

            # Calculate calls and wins
            if trump_maker.team == 1:
                team1_calls += 1
                if going_alone:
                    team1_loner_attempts += 1
                    if team1_points == 4:
                        team1_loner_wins += 1
                if team1_points > team2_points:
                    team1_wins += 1
                    if team1_points == 2:
                        team1_marches += 1
            else:
                team2_calls += 1
                if going_alone:
                    team2_loner_attempts += 1
                    if team2_points == 4:
                        team2_loner_wins += 1
                if team2_points > team1_points:
                    team2_wins += 1
                    if team2_points == 2:
                        team2_marches += 1


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

        loner_rates_round1 = {
            name: round(loner_attempts_round1[name] / num_simulations * 100, 2)
            for name in loner_attempts_round1
        }
        loner_rates_round2 = {
            name: round(loner_attempts_round2[name] / num_simulations * 100, 2)
            for name in loner_attempts_round2
        }
        total_loner_rates = {
            name: round((loner_attempts_round1[name] + loner_attempts_round2[name]) / num_simulations * 100, 2)
            for name in loner_attempts_round1
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

        print(f"Loner rates in round 1 after {num_simulations} simulations:")
        for name, rate in loner_rates_round1.items():
            print(f"{name}: {rate}%")

        print(f"Loner rates in round 2 after {num_simulations} simulations:")
        for name, rate in loner_rates_round2.items():
            print(f"{name}: {rate}%")

        print(f"Total loner rates after {num_simulations} simulations:")
        for name, rate in total_loner_rates.items():
            print(f"{name}: {rate}%")


        # Calculate win rates
        if team1_calls != 0:
            print(f"Team 1 wins: {team1_wins}")
            print(f"Team 1 calls: {team1_calls}")
            team1_win_rate = (team1_wins / team1_calls) * 100
        else:
            team1_win_rate = 0
        if team2_calls != 0:
            print(f"Team 2 wins: {team2_wins}")
            print(f"Team 2 calls: {team2_calls}")
            team2_win_rate = (team2_wins / team2_calls) * 100
        else:
            team2_win_rate = 0

        print(f"Team 1 win rate after {num_simulations} simulations: {team1_win_rate}%")
        print(f"Team 2 win rate after {num_simulations} simulations: {team2_win_rate}%")

        # Print points per hand for each team
        print(f"Team 1 points per hand: {team1_total_points / num_simulations}")
        print(f"Team 2 points per hand: {team2_total_points / num_simulations}")

        if team1_marches != 0:
            team1_marches_rate = (team1_marches / team1_calls) * 100
            print(f"Team 1 marches: {team1_marches_rate}%")
        if team2_marches != 0:
            team2_marches_rate = (team2_marches / team2_calls) * 100
            print(f"Team 2 marches: {team2_marches_rate}%")

        if team1_loner_attempts != 0:
            team1_loner_success_rate = (team1_loner_wins / team1_loner_attempts) * 100
            print(f"Team 1 loner success rate: {team1_loner_success_rate:.2f}%")
        if team2_loner_attempts != 0:
            team2_loner_success_rate = (team2_loner_wins / team2_loner_attempts) * 100
            print(f"Team 2 loner success rate: {team2_loner_success_rate:.2f}%")
        # Total loner success rate
        if team1_loner_attempts + team2_loner_attempts != 0:
            total_loner_success_rate = ((team1_loner_wins + team2_loner_wins) / (team1_loner_attempts + team2_loner_attempts)) * 100
            print(f"Total loner success rate: {total_loner_success_rate:.2f}%")


    def play_hand(self, dealt_hands, players, trump_suit, trump_maker, going_alone):
        """
        Plays a hand of Euchre
        """

        previous_tricks = {}
        team1_tricks = 0
        team2_tricks = 0

        # Create copy of players list to keep track of player order
        play_order = players[:]

        # If going alone, remove partner from play order and remove their hand
        if going_alone:
            partner = next(p for p in play_order if p.name == trump_maker.partner)
            play_order.remove(partner)
            del dealt_hands[partner.name]

        for trick_number in range(1, 6):
            played_cards = []

            # Each player plays a card
            for bot in play_order:
                card_to_play = bot.determine_best_card(
                    hand=dealt_hands[bot.name],
                    trump_suit=trump_suit,
                    played_cards=played_cards,
                    previous_tricks=previous_tricks,
                    trump_caller=trump_maker,
                    going_alone=going_alone,
                    tricks_won=team1_tricks if bot.team == 1 else team2_tricks
                )

                dealt_hands[bot.name].remove(card_to_play)

                played_cards.append(PlayedCard(card=card_to_play, player=bot))

            # Determine the winner of the trick
            winner = self.evaluate_trick_winner(trump_suit, played_cards)

            # Add the played cards to the previous cards
            previous_tricks[trick_number] = played_cards

            # Add 1 to the number of tricks the winner has in the original player list
            if winner.team == 1:
              team1_tricks += 1
            elif winner.team == 2:
              team2_tricks += 1

            # Rotate the players list so that the winner leads the next trick
            winner_idx = play_order.index(winner)
            play_order = play_order[winner_idx:] + play_order[:winner_idx]

        return self.evaluate_points(team1_tricks, team2_tricks, trump_maker, going_alone)

    def evaluate_trick_winner(self, trump_suit, played_cards):
        """
        Evaluates the winner of the trick
        """
        # Get the lead suit
        if played_cards[0].card.is_left_bower(trump_suit):
            lead_suit = played_cards[0].card.next_suit()
        else:
            lead_suit = played_cards[0].card.suit
        
        winning_card = max(played_cards, key=lambda pc: BotLogic.euchre_rank(pc.card, trump_suit, lead_suit))
        
        return winning_card.player

    def evaluate_points(self, team1_tricks, team2_tricks, trump_maker, went_alone):
        """
        Evaluates the points for each team based on how many tricks they took
        """
        # 1 point if you call it and win 3 tricks
        # 2 points if you call it and win 5 tricks
        # 2 points if the other team calls it and you win 3 tricks
        # 4 points if you win all 5 tricks when going alone
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
                if went_alone and team1_tricks == 5:
                    team1_points += 4
                else:
                    team1_points += 1 if team1_tricks < 5 else 2
            else:
                # Team 1 euchred the other team
                team1_points += 2
        if team2_tricks >= 3:
            if trump_calling_team == 2:
                # Team 2 called trump and won
                if went_alone and team2_tricks == 5:
                    team2_points += 4
                else:
                    team2_points += 1 if team2_tricks < 5 else 2
            else:
                # Team 2 euchred the other team
                team2_points += 2

        return team1_points, team2_points

    def convert_to_cards(self, string_cards, player):
        dummy_hand = []
        for card_str in string_cards:
            rank, suit = card_str.split(" of ")
            dummy_card = Card(rank=rank, suit=suit)
            dummy_hand.append(dummy_card)
        return dummy_hand        
    
    def print_hand_scores(self, hand_str, trump_suit):
        """
        Takes a string of cards and prints out the score for that hand in each suit or a specific trump suit.
        
        For debugging purposes
        """

        bot = Bot("Bot", partner="Bot", team=1)

        # Convert string to list of cards
        hand = []
        for card_str in hand_str.split(", "):
            rank, suit = card_str.split(" of ")
            hand.append(Card(rank=rank, suit=suit))
            
        print(f"\nScoring hand: {hand_str}")
        print("---------------")

        # Score hand in specified trump suit only
        trump_score = bot.evaluate_trump(hand, trump_suit)
        aces_score = bot.evaluate_aces(hand, trump_suit)
        voids_score = bot.evaluate_voids(hand, trump_suit)
        total_score = bot.evaluate_hand(hand, trump_suit)
        
        print(f"{trump_suit.capitalize()}:")
        print(f"  Trump Score: {trump_score:.3f} * 0.7 = {trump_score * 0.7:.3f}")
        print(f"  Aces Score: {aces_score:.3f} * 0.2 = {aces_score * 0.2:.3f}")
        print(f"  Voids Score: {voids_score:.3f} * 0.1 = {voids_score * 0.1:.3f}")
        print(f"  Total Score: {total_score:.3f}")

        
if __name__ == "__main__":
    simulation = MonteCarloSimulation()
    simulation.run_simulation(1000000)
    # simulation.print_hand_scores("A of diamonds, A of hearts, J of spades, J of diamonds, J of hearts", "diamonds")
