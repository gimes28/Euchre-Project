class BotLogic:    
    SUIT_PAIRS = {
        'hearts': 'diamonds',
        'diamonds': 'hearts',
        'clubs': 'spades',
        'spades': 'clubs'
    }

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
                temp_hand = list(hand)
                temp_hand.append(up_card)

                # Discard a card
                discarded_card = self.get_worst_card(temp_hand, up_card.suit)
                temp_hand.remove(discarded_card)

                hand_score = self.evaluate_hand(temp_hand, trump_suit)
                # print(f"Dealer {self.name} hand score: {hand_score}")
            else:
                hand_score = self.evaluate_hand(hand, trump_suit)
                # print(f"Player {self.name} hand score: {hand_score}")

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

    def determine_best_card(self, hand, trump_suit, played_cards, previous_tricks, trump_caller):
        """
        Determines the best card to play in a trick
        """

        if len(hand) == 1:
            return hand[0]

        partner_called_trump = trump_caller.name == self.partner
        player_called_trump = trump_caller.name == self.name
        opponent_called_trump = not partner_called_trump and not player_called_trump # TODO: It can be useful to know which opponent called trump specifically as that can change the card to play

        # Check if you are leading
        if not played_cards:
            # Decide what card to lead
            return self.choose_lead_card(hand, trump_suit, previous_tricks, partner_called_trump, player_called_trump, opponent_called_trump)
        
        # Not leading, so get suit that was lead
        if played_cards[0].card.is_left_bower(trump_suit):
            lead_suit = played_cards[0].card.next_suit()
        else:
            lead_suit = played_cards[0].card.suit

        # Find winner of current trick
        winning_played_card = max(played_cards, key=lambda x: BotLogic.euchre_rank(x.card, trump_suit, lead_suit))
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
        lowest_card = min(hand, key=lambda x: BotLogic.euchre_rank(x, trump_suit, lead_suit))

        if lead_suit_cards:
            high_lead = max(lead_suit_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit, lead_suit))
            low_lead = min(lead_suit_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit, lead_suit))

            # Follow suit
            if is_partner_winning:
                if player_is_last_to_play:
                    # Partner already has the trick won, so play lowest card
                    return low_lead
                elif self.is_boss_card(winning_played_card.card, previous_tricks, trump_suit):
                    # If partner is winning with a boss card, play lowest card
                    return low_lead
                else:
                    # If partner is not winning with a boss card, play highest card if you can win trick
                    if BotLogic.euchre_rank(high_lead, trump_suit) > BotLogic.euchre_rank(winning_played_card.card, trump_suit):
                        return high_lead
            else:
                # Opponent is winning, so play highest card if you can win trick
                if BotLogic.euchre_rank(high_lead, trump_suit) > BotLogic.euchre_rank(winning_played_card.card, trump_suit):
                    return high_lead
                
            return low_lead
        
        played_trump_cards = self.get_trump_cards([card.card for card in played_cards], trump_suit)
        
        if not played_trump_cards:
            if trump_cards:
                small_trump = min(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
                if is_partner_winning:
                    if player_is_last_to_play:
                        return lowest_card
                    elif not self.is_boss_card(winning_played_card.card, previous_tricks, trump_suit):
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
            winning_trump_cards = [card for card in trump_cards if BotLogic.euchre_rank(card, trump_suit) > BotLogic.euchre_rank(winning_played_card.card, trump_suit)]
            if winning_trump_cards:
                # Play the highest trump necessary to take the lead
                return min(winning_trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            else:
                # Cannot win trick, so play lowest card # TODO: making a void could be more valuable than playing lowest card
                return lowest_card  

    def choose_lead_card(self, hand, trump_suit, previous_tricks, partner_called_trump, player_called_trump, opponent_called_trump):
        """
        Determines the best card to lead with
        """
        trump_cards = self.get_trump_cards(hand, trump_suit)

        # Get all cards that are the highest card in the suit remaining
        boss_cards = self.get_boss_cards_in_hand(hand, previous_tricks, trump_suit)
        non_trump_boss = [card for card in boss_cards if card.suit != trump_suit and not card.is_left_bower(trump_suit)]
        have_highest_trump = self.has_boss_card(hand, trump_suit, previous_tricks, trump_suit)
        trump_was_led_before = any((trick_cards[0].card.suit == trump_suit or trick_cards[0].card.is_left_bower(trump_suit)) for trick_cards in previous_tricks.values())

        # If you have highest trump card and a offsuit boss card, lead the trump then the boss card
        if have_highest_trump and non_trump_boss:
            if player_called_trump or partner_called_trump or (opponent_called_trump and trump_was_led_before):
                return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
        
        # On second to last trick, if you have one trump and one offsuit, lead the offsuit
        if len(previous_tricks) == 3 and len(hand) == 2:
            if len(trump_cards) == 1:
                return min(hand, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # Lead strong if partner called trump
        if partner_called_trump and trump_cards:
            # Do not lead a trump card if trump has already been led in a previous trick
            if not trump_was_led_before or (len(trump_cards) > 1 and non_trump_boss):
                return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # If you called trump and have highest trump, lead it
        if player_called_trump:
            if have_highest_trump:
                return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            elif len(trump_cards) > 1:
                return min(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # If opponents called, lead boss off suit if you have it or lead low
        if opponent_called_trump:
            if non_trump_boss:
                return max(non_trump_boss, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            else:
                return min(hand, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            
        # Lead highest off suit if it is a boss card
        if non_trump_boss:
            return max(non_trump_boss, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # Otherwise, create void is possible or lead lowest card
        return self.get_worst_card(hand, trump_suit)

    def get_boss_cards_in_hand(self, hand, previous_tricks, trump_suit):
        """
        Determines all boss cards in hand
        """
        boss_cards = []
        for card in hand:
            if self.is_boss_card(card, previous_tricks, trump_suit):
                boss_cards.append(card)
        return boss_cards
    
    def get_boss_card(self, suit, previous_tricks, is_trump=False):
        """
        Determines the highest card of the highest rank remaining in the suit
        """
        card_ranks = ["A", "K", "Q", "J", "10", "9"]

        if is_trump:
            all_previous_cards = [card for trick in previous_tricks.values() for card in trick]
            # Deal with bowers
            if not any(played_card.card.is_right_bower(suit) for played_card in all_previous_cards):
                return "J", suit
            elif not any(played_card.card.is_left_bower(suit) for played_card in all_previous_cards):
                return "J", BotLogic.SUIT_PAIRS[suit] # Get left bower suit

            # Both bowers have been played already    
            card_ranks.remove("J")

        # Get all previous cards of the relevant suit
        relevant_previous_cards = [card for trick_cards in previous_tricks.values() for card in trick_cards if card.card.suit == suit]

        for card in relevant_previous_cards:
            if card.card.rank in card_ranks:
                card_ranks.remove(card.card.rank)

        if card_ranks == []:
            return None, None

        return card_ranks[0], suit
        
    def is_boss_card(self, card, previous_cards, trump_suit):
        """
        Determines if a card is the highest card of the highest rank remaining in the suit
        """
        highest_card_rank, highest_card_suit = self.get_boss_card(card.suit, previous_cards, (card.suit == trump_suit or card.is_left_bower(trump_suit)))

        return card.rank == highest_card_rank and card.suit == highest_card_suit

    def has_boss_card(self, hand, suit, previous_cards, trump_suit):
        """
        Determines if the hand has a boss card in the given suit
        """
        highest_card_rank, highest_card_suit = self.get_boss_card(suit, previous_cards, suit == trump_suit)

        if not highest_card_rank:
            return False

        return any(card.rank == highest_card_rank and card.suit == highest_card_suit for card in hand)
                
    def get_trump_cards(self, hand, trump_suit):
        return [card for card in hand if card.suit == trump_suit or card.is_left_bower(trump_suit)]

    def get_worst_card(self, hand, trump_suit):
        """
        Choose a card to discard based on creating a suit void if possible
        """
        trump_cards = self.get_trump_cards(hand, trump_suit)
        non_trump_cards = [card for card in hand if card not in trump_cards]

        if not non_trump_cards:
            # Hand is all trump cards, so discard lowest trump card
            return min(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
        
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
            return min(possible_voids, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
        
        # If no possible voids, discard lowest non-trump card
        return min(non_trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))