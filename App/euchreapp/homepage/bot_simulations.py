from bot_logic import BotLogic
import pandas as pd
import os
import random


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_storage")

FILENAME = os.path.join(DATA_DIR, "game_data.csv")

COLUMNS = [ "game_id", "round_id", "team1_score", "team2_score",
            "team1_round_score", "team2_round_score",
            "seat_position", "is_dealer", "partner_is_dealer",
            "trump_suit", "trump_maker", "hand", "current_trick", 
            "suit_lead", "up_card", "known_cards", "card_to_evaluate", 
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
    
    def get_card(self):
        return f"{self.card.rank} of {self.card.suit}"
    
class MonteCarloSimulation():
    def __init__(self):
        # Track stats by seat position rather than by bot
        self.positions = ['first', 'second', 'third', 'dealer']

        # Track number of hands
        self.num_total_hands = 0

        # Track number of calls and wins
        self.calls_round1 = {position: 0 for position in self.positions}
        self.calls_round2 = {position: 0 for position in self.positions}
        self.wins_round1 = {position: 0 for position in self.positions}
        self.wins_round2 = {position: 0 for position in self.positions}
        self.euchre_round1 = {position: 0 for position in self.positions}
        self.euchre_round2 = {position: 0 for position in self.positions}
        self.total_points = {position: 0 for position in self.positions}
        self.total_calls = {position: 0 for position in self.positions}
        self.total_wins = {position: 0 for position in self.positions}
        self.total_euchres = {position: 0 for position in self.positions}

        self.player_card_stats = {}

        # Track team-level data
        self.team_calls = {1: 0, 2: 0}
        self.team_wins = {1: 0, 2: 0}
        self.team_euchres = {1: 0, 2: 0}
        self.team_points = {1: 0, 2: 0}

        # Track loner attempts
        self.loner_attempts_round1 = {position: 0 for position in self.positions}
        self.loner_attempts_round2 = {position: 0 for position in self.positions}
        self.loner_wins_round1 = {position: 0 for position in self.positions}
        self.loner_wins_round2 = {position: 0 for position in self.positions}
        self.total_loner_attempts = {position: 0 for position in self.positions}
        self.total_loner_wins = {position: 0 for position in self.positions}
        self.team_loner_attempts = {1: 0, 2: 0}
        self.team_loner_wins = {1: 0, 2: 0}

    def initialize_bots(self):
        bots = [
            Bot(name="Player", partner="Team Mate", team=1),
            Bot(name="Opponent1", partner="Opponent2", team=2),
            Bot(name="Team Mate", partner="Player", team=1),
            Bot(name="Opponent2", partner="Opponent1", team=2)
        ]
        # Initialize tracking
        # for bot in bots:
        #     self.calls_round1[bot.name] = 0
        #     self.calls_round2[bot.name] = 0
        #     self.wins_round1[bot.name] = 0
        #     self.wins_round2[bot.name] = 0
        #     self.euchre_round1[bot.name] = 0
        #     self.euchre_round2[bot.name] = 0
        #     self.total_calls[bot.name] = 0
        #     self.total_wins[bot.name] = 0
        #     self.total_euchres[bot.name] = 0
        #     self.total_points[bot.name] = 0
        #     self.dealer_count[bot.name] = 0
        #     self.dealer_calls[bot.name] = 0
        #     self.dealer_points[bot.name] = 0
        #     self.loner_attempts_round1[bot.name] = 0
        #     self.loner_attempts_round2[bot.name] = 0
        #     self.loner_wins_round1[bot.name] = 0
        #     self.loner_wins_round2[bot.name] = 0
        #     self.total_loner_attempts[bot.name] = 0
        #     self.total_loner_wins[bot.name] = 0

        return bots

    def run_simulation(self, num_simulations=1000):
        """
        Runs a simulation to determine the call percentage for each seat position in order to tweak thresholds and strategy weights
        """
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

            # Randomly select dealer
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
                self.num_total_hands += 1
                
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
                            self.track_call_data(bot, trump_round, dealer, going_alone, bot.get_seat_position(players))
                            trump_maker = bot

                            if trump_round == 1:

                                dealt_hands[dealer.name].append(up_card)
                                
                                discarded_card = dealer.get_worst_card(dealt_hands[dealer.name], up_card.suit)
                                dealt_hands[dealer.name].remove(discarded_card)
                            break

                    if trump_maker:
                        break

                # Use this to get stats on how many times each call was successful or euchred
                team1_p, team2_p = self.play_hand(game_num, team1_points, team2_points, dealt_hands, players, trump_decision, trump_maker, up_card, dealer, going_alone)

                team1_points += team1_p
                team2_points += team2_p

                self.track_results(trump_maker, team1_p, team2_p, trump_round, dealer, going_alone, trump_maker.get_seat_position(players))

            # Show results of each game
            if not game_num % 100:
                print (f'Game number: {game_num}/{num_simulations}')
                print(f'Time elapsed: {(time.time() - start_time)/60:.2f} min')

        #self.display_results(num_simulations)
        print (f'Games are complete')
        print(f'Total Time elapsed: {(time.time() - start_time)/60:.2f} min')

    def track_call_data(self, bot, trump_round, dealer, going_alone, position):
        if trump_round == 1:
            self.calls_round1[position] += 1
            if going_alone:
                self.loner_attempts_round1[position] += 1
        else:
            self.calls_round2[position] += 1
            if going_alone:
                self.loner_attempts_round2[position] += 1
        self.total_calls[position] += 1
        self.team_calls[bot.team] += 1
        if going_alone:
            self.team_loner_attempts[bot.team] += 1
            self.total_loner_attempts[position] += 1

    def track_results(self, trump_maker, team1_p, team2_p, trump_round, dealer, going_alone, position):
        calling_team_won = (team1_p > team2_p and trump_maker.team == 1) or (team2_p > team1_p and trump_maker.team == 2)
        points_earned = team1_p if trump_maker.team == 1 else team2_p
        self.total_points[position] += team1_p if trump_maker.team == 1 else team2_p

        if calling_team_won:
            self.total_wins[position] += 1
            self.team_wins[trump_maker.team] += 1
            if trump_round == 1:
              self.wins_round1[position] += 1
            else:
              self.wins_round2[position] += 1
        else:
            self.total_euchres[position] += 1
            self.team_euchres[trump_maker.team] += 1

        if going_alone and calling_team_won and points_earned == 4:
            if trump_round == 1:
                self.loner_wins_round1[position] += 1
            else:
                self.loner_wins_round2[position] += 1
            self.total_loner_wins[position] += 1
            self.team_loner_wins[trump_maker.team] += 1
    
    def display_results(self, num_simulations):
        print("\n--- Results ---")
        print(f"Total Simulations: {num_simulations}")

        for position in self.positions:
            print(f"\n{position} seat:")

            # Calculate percentages
            win_rate = (self.total_wins[position] / self.total_calls[position]) * 100 if self.total_calls[position] > 0 else 0
            first_round_rate = (self.wins_round1[position] / self.calls_round1[position]) * 100 if self.calls_round1[position] > 0 else 0
            second_round_rate = (self.wins_round2[position] / self.calls_round2[position]) * 100 if self.calls_round2[position] > 0 else 0
            euchre_rate = (self.total_euchres[position] / self.total_calls[position]) * 100 if self.total_calls[position] > 0 else 0
            avg_points_per_call = self.total_points[position] / self.total_calls[position] if self.total_calls[position] > 0 else 0
            call_rate = (self.total_calls[position] / self.num_total_hands) * 100
            loner_call_rate = (self.total_loner_attempts[position] / self.total_calls[position]) * 100 if self.total_calls[position] > 0 else 0
            loner_win_rate = (self.total_loner_wins[position] / self.total_loner_attempts[position]) * 100 if self.total_loner_attempts[position] > 0 else 0
 
            print(f"  Call Rate: {call_rate:.2f}%")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  First Round Win Rate: {first_round_rate:.2f}%")
            print(f"  Second Round Win Rate: {second_round_rate:.2f}%")
            print(f"  Euchre Rate: {euchre_rate:.2f}%")
            print(f"  Avg Points Per Call: {avg_points_per_call:.2f}")
            print(f"  Loner Call Rate: {loner_call_rate:.2f}%")
            print(f"  Loner Win Rate: {loner_win_rate:.2f}%")

        for team in (1, 2):
            print(f"\nTeam {team}:")
            print(f"  Total Calls: {self.team_calls[team]}")
            print(f"  Total Wins: {self.team_wins[team]}")
            print(f"  Total Euchres: {self.team_euchres[team]}")
            print(f"  Team Loner Attempts: {self.team_loner_attempts[team]}")
            print(f"  Team Loner Wins: {self.team_loner_wins[team]}")

    def play_hand(self, game_num, team1_points, team2_points, dealt_hands, players, trump_suit, trump_maker, up_card, dealer, going_alone):
        """
        Plays a hand of Euchre
        """

        previous_tricks = {}
        team_tricks = [0, 0]
        player_card_played = None

        # Create copy of players list to keep track of player order
        play_order = players[:]

        # If going alone, remove partner from play order and remove their hand
        if going_alone:
            partner = next(p for p in play_order if p.name == trump_maker.partner)
            play_order.remove(partner)
            del dealt_hands[partner.name]

        for trick_number in range(1, 6):
            # played cards for each trick
            played_cards = []
            suit_lead = "unknown"
            # Each player plays a card
            for bot in play_order:
                card_to_play = bot.determine_best_card(
                    hand=dealt_hands[bot.name],
                    trump_suit=trump_suit,
                    played_cards=played_cards,
                    previous_tricks=previous_tricks,
                    trump_caller=trump_maker,
                    going_alone=going_alone,
                    tricks_won=team_tricks[bot.team - 1]
                )
                
                if(bot.name == "Player"):
                    # Perform montecarlo simulation for exploring each card in hard
                    card_probs = self.monte_carlo_card_evaluator( original_state={ "dealt_hands": dealt_hands, 
                                                                                  "previous_tricks": previous_tricks},
                                                                  player_hand=dealt_hands["Player"], play_order=players,
                                                                  trump_suit=trump_suit, trump_maker=trump_maker,
                                                                  going_alone=going_alone, team_tricks=team_tricks,
                                                                  num_simulations=25)

                    self.update_game_state(game_num, trick_number, team1_points, team2_points,
                        team_tricks, dealer, play_order, players, trump_maker, trump_suit, dealt_hands, 
                        card_to_play, up_card, played_cards, previous_tricks, suit_lead, card_probs)
                   
                    # Find suit lead at beginning of trick if player is first
                    if "Player" == play_order[0].name:
                        suit_lead = card_to_play.suit
                    
                    player_card_played = card_to_play
                    player_team = bot.team
                
                # Find suit lead at beginning of trick
                if bot.name == play_order[0].name:
                    suit_lead = card_to_play.suit

                dealt_hands[bot.name].remove(card_to_play)

                played_cards.append(PlayedCard(card=card_to_play, player=bot))

            # Determine the winner of the trick
            winner = self.evaluate_trick_winner(trump_suit, played_cards)

            # Add the played cards to the previous cards
            previous_tricks[trick_number] = played_cards

            winning_team = winner.team

            # Team 1 points at index 0 and Team 2 points at index 1
            team_tricks[winning_team - 1] += 1


            #print(f"Team 1 tricks: {team_tricks[0]}, Team 2 tricks: {team_tricks[1]}")

            # Rotate the players list so that the winner leads the next trick
            winner_idx = play_order.index(winner)
            play_order = play_order[winner_idx:] + play_order[:winner_idx]

            team1_p, team2_p = self.evaluate_points(team_tricks[0], team_tricks[1], trump_maker, going_alone)

            team1_points = team1_p
            team2_points = team2_p

        # Track result for players card
        if player_card_played:
            card_key = f"{player_card_played.rank} of {player_card_played.suit}"
            if card_key not in self.player_card_stats:
                self.player_card_stats[card_key] = {'wins': 0, 'total': 0}

            self.player_card_stats[card_key]['total'] += 1

            player_team_won = (team1_points > team2_points and player_team == 1) or (team2_points > team1_points and player_team == 2)
            if player_team_won:
                self.player_card_stats[card_key]['wins'] += 1

        return team1_points, team2_points

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
        # 1 point if you call it and win 3 or 4 tricks
        # 2 points if you call it and win 5 tricks
        # 2 points if the other team calls it and you win at least 3 tricks
        # 4 points if you win all 5 tricks when going alone

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
    

    def update_game_state(self, game_num, trick_number, team1_points, team2_points,
                      team_tricks, dealer, play_order, players, trump_maker, trump_suit,
                      dealt_hands, best_card, up_card, played_cards, previous_tricks, suit_lead, card_probs):

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
                    
        # Find all cards played
        previous_cards = [card for trick in previous_tricks.values() for card in trick]
        known_cards = []
        known_cards.extend([str(card.card) for card in previous_cards])
        player_hand = [str(c) for c in player_hand]
        current_trick = [str(c.card) for c in played_cards]

        # Generate one row per card in the hand
        for card in player_hand:
            game_state = {
                "game_id": game_num,
                "round_id": trick_number,
                "team1_score": team1_points,
                "team2_score": team2_points,
                "team1_round_score": team_tricks[0],
                "team2_round_score": team_tricks[1],
                "seat_position": index,
                "is_dealer": dealer.name == "Player",
                "partner_is_dealer": dealer.team == player.team and dealer.name != "Player",
                "trump_suit": trump_suit,
                "trump_maker": trump_maker.name,
                "hand": player_hand,
                "current_trick": current_trick,
                "suit_lead": suit_lead,
                "up_card": str(up_card),
                "known_cards": known_cards,
                "card_to_evaluate": str(card),
                "card_to_play": 1 if card == str(best_card) else 0,
                "win_probability": card_probs[str(card)]
            }

            Table.update_table(game_state)  # Update table with each card as a row

        return  # You no longer return a single game_state, as you log multiple rows

    def monte_carlo_card_evaluator(self, original_state, player_hand, play_order, trump_suit, trump_maker, going_alone, team_tricks, num_simulations=50):
        """
        Simulates N games for each card in the player's hand to estimate win probability.
        """
        import copy
        from collections import defaultdict

        card_win_stats = defaultdict(lambda: {'wins': 0, 'total': 0})
        player_team = [bot for bot in play_order if bot.name == "Player"][0].team

        # Create a deck of all possible (excluding the player's hand and the previous cards)
        suits = ["hearts", "diamonds", "clubs", "spades"]
        ranks = ["A", "K", "Q", "J", "10", "9"]
        all_cards = [Card(rank=rank, suit=suit) for suit in suits for rank in ranks]
        
        sim_previous_tricks = copy.deepcopy(original_state["previous_tricks"])

        # Remove the player's hand and the previous cards
        known_cards = []
        for card in player_hand:
            known_cards.append(card)
        for card in sim_previous_tricks:
            known_cards.append(card)

        unknown_cards = [card for card in all_cards if card not in known_cards]

        for card in player_hand:
            card_str = str(card)

            for _ in range(num_simulations):
                # Deep copy the game state so each sim is fresh
                # sim_hands = copy.deepcopy(original_state["dealt_hands"])
                sim_players = copy.deepcopy(play_order)

                # Force player to play this card first
                sim_hands = {}
                sim_hands["Player"] = [c for c in player_hand if str(c) != card_str]
                remaining_cards = unknown_cards.copy()
                random.shuffle(remaining_cards)

                # Deal bot hands randomly from list of possible cards
                card_index = 0
                for bot in sim_players:
                    if bot.name != "Player":
                        cards_to_deal = 5 - len(sim_previous_tricks)
                        bot_cards = remaining_cards[card_index:card_index + cards_to_deal]
                        sim_hands[bot.name] = bot_cards
                        card_index += cards_to_deal

                trick = [PlayedCard(card=card, player=bot)]

                # Let others play their card in this trick using minimal logic
                for bot in sim_players:
                    if bot.name == "Player":
                        continue

                    hand = sim_hands[bot.name]
                    if not hand:
                        continue  # Skip if no cards left

                    card_to_play = bot.determine_best_card( 
                        sim_hands[bot.name],
                        trump_suit, 
                        trick, 
                        sim_previous_tricks,
                        trump_maker,
                        going_alone,
                        team_tricks[bot.team - 1]
                    )
                    
                    sim_hands[bot.name].remove(card_to_play)
                    trick.append(PlayedCard(card=card_to_play, player=bot))

                # Determine winner of trick 
                winner = self.evaluate_trick_winner(trump_suit, trick)

                # Randomly simulate remaining tricks (or use further logic)
                new_team_tricks = [0, 0]
                winning_team = winner.team
                new_team_tricks[winning_team - 1] += 1

                # Simulate 4 more tricks with simplified logic
                for _ in range(4):
                    trick = []
                    for bot in sim_players:
                        hand = sim_hands[bot.name]
                        if hand:
                            card_to_play = bot.determine_best_card( 
                                sim_hands[bot.name],
                                trump_suit, trick, 
                                sim_previous_tricks,
                                trump_maker,
                                going_alone,
                                team_tricks[bot.team - 1]
                            )
                            
                            sim_hands[bot.name].remove(card_to_play)
                            trick.append(PlayedCard(card=card_to_play, player=bot))
                    if trick:
                        winner = self.evaluate_trick_winner(trump_suit, trick)
                        new_team_tricks[winner.team - 1] += 1

                # Evaluate points
                team1_points, team2_points = self.evaluate_points(new_team_tricks[0], new_team_tricks[1], trump_maker, going_alone)

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
if __name__ == "__main__":
   simulation = MonteCarloSimulation()
   simulation.run_simulation(2000)
