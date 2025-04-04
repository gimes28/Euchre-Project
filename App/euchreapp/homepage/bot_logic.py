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

        # Thresholds for both rounds of trump selection
        thresholds = {
            'round1': {
                'first': {
                    'normal': 0.33,
                    'loner': 0.51
                },
                'second': {
                    'normal': 0.225,
                    'loner': 0.451
                },
                'third': {
                    'normal': 0.355,
                    'loner': 0.525
                },
                'dealer': {
                    'normal': 0.26,
                    'loner': 0.47
                }
            },
            'round2': {
                'first': {
                    'next': {
                        'normal': 0.2,
                        'loner': 0.45
                    },
                    'reverse': {
                        'normal': 0.315,
                        'loner': 0.48
                    }
                },
                'second': {
                    'next': {
                        'normal': 0.315,
                        'loner': 0.48
                    },
                    'reverse': {
                        'normal': 0.2,
                        'loner': 0.45
                    }
                },
                'third': {
                    'next': {
                        'normal': 0.23,
                        'loner': 0.465
                    },
                    'reverse': {
                        'normal': 0.305,
                        'loner': 0.485
                    }
                },
                'dealer': {
                    'next': {
                        'normal': 0.35,
                        'loner': 0.46
                    },
                    'reverse': {
                        'normal': 0.3,
                        'loner': 0.45
                    }
                }
            }
        }

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
            else:
                hand_score = self.evaluate_hand(hand, trump_suit)

            first_round_thresholds = thresholds['round1']

            position_threshold = first_round_thresholds[position]
            # Go alone if hand is strong enough. However, if the up card is the right bower, first and third seat should not go alone
            will_go_alone = hand_score >= position_threshold['loner'] and (up_card.rank != 'J' or position not in ['first', 'third'])

            decision = trump_suit if hand_score >= position_threshold['normal'] else 'pass'

            # If you are in first seat with a callable hand, you should compare to the second round threshold because you will get first chance to call
            if position == 'first' and decision != 'pass':
                next_hand_score = self.evaluate_hand(hand, self.SUIT_PAIRS[trump_suit])
                hand_score_margin = hand_score - position_threshold['normal']
                next_hand_score_margin = next_hand_score - thresholds['round2'][position]['next']['normal']

                if next_hand_score_margin > hand_score_margin:
                    decision = 'pass'
                    will_go_alone = False
            
            return decision, will_go_alone
        
        if trump_round == "2":

            second_round_thresholds = thresholds['round2']

            next_suit = up_card.next_suit()

            suits = ["hearts", "diamonds", "clubs", "spades"]
            reverse_suits = [suit for suit in suits if suit not in [trump_suit, next_suit]]

            seat_thresholds = second_round_thresholds[position]

            next_suit_score = self.evaluate_hand(hand, next_suit)
            reverse_suit_score_1 = self.evaluate_hand(hand, reverse_suits[0])
            reverse_suit_score_2 = self.evaluate_hand(hand, reverse_suits[1])

            decision = 'pass'
            will_go_alone = False
            
            if self.name == dealer.name:
                next_margin = next_suit_score - seat_thresholds['next']['normal']
                reverse_margin_1 = reverse_suit_score_1 - seat_thresholds['reverse']['normal']
                reverse_margin_2 = reverse_suit_score_2 - seat_thresholds['reverse']['normal']

                options = [
                    (next_suit, next_margin, next_suit_score >= seat_thresholds['next']['loner']),
                    (reverse_suits[0], reverse_margin_1, reverse_suit_score_1 >= seat_thresholds['reverse']['loner']),
                    (reverse_suits[1], reverse_margin_2, reverse_suit_score_2 >= seat_thresholds['reverse']['loner'])
                ]

                best_option = max(options, key=lambda x: x[1])
                decision = best_option[0]
                will_go_alone = best_option[2]

            else:
                should_call_next = next_suit_score >= seat_thresholds['next']['normal']
                should_go_alone_next = next_suit_score >= seat_thresholds['next']['loner']
                should_call_reverse = reverse_suit_score_1 >= seat_thresholds['reverse']['normal'] or reverse_suit_score_2 >= seat_thresholds['reverse']['normal']
                should_go_alone_reverse = reverse_suit_score_1 >= seat_thresholds['reverse']['loner'] or reverse_suit_score_2 >= seat_thresholds['reverse']['loner']

                # If all suits are higher than threshold, choose the suit that is greater than the threshold by the most
                if should_call_next and should_call_reverse:
                    next_margin = next_suit_score - seat_thresholds['next']['normal']
                    reverse_margin_1 = reverse_suit_score_1 - seat_thresholds['reverse']['normal']
                    reverse_margin_2 = reverse_suit_score_2 - seat_thresholds['reverse']['normal']

                    if next_margin >= reverse_margin_1 and next_margin >= reverse_margin_2:
                        decision = next_suit
                        will_go_alone = should_go_alone_next
                    else:
                        decision = reverse_suits[0] if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suits[1]
                        will_go_alone = should_go_alone_reverse
                elif should_call_next:
                    decision = next_suit
                    will_go_alone = should_go_alone_next
                elif should_call_reverse:
                    decision = reverse_suits[0] if reverse_suit_score_1 >= reverse_suit_score_2 else reverse_suits[1]
                    will_go_alone = should_go_alone_reverse
            
            return decision, will_go_alone
        
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
            'trump_cards': 0.7,
            'off_aces': 0.2,
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

        trump_cards = self.get_trump_cards(hand, trump_suit)

        trump_ranks = {"right": 1.0, "left": 0.9, "A": 0.8, "K": 0.7, "Q": 0.6, "10": 0.575, "9": 0.55}

        trump_score = 0
        has_right_bower = False
        has_left_bower = False

        for card in trump_cards:
            if card.is_right_bower(trump_suit):
                trump_score += trump_ranks["right"]
                has_right_bower = True
            elif card.is_left_bower(trump_suit):
                trump_score += trump_ranks["left"]
                has_left_bower = True
            elif card.suit == trump_suit:
                trump_score += trump_ranks[card.rank]

        multiplier = 1.0
        num_trump = len(trump_cards)

        if num_trump == 3:
            multiplier = 1.4
        elif num_trump == 4:
            multiplier = 1.6
        elif num_trump == 5:
            multiplier = 1.8

        if has_right_bower and has_left_bower:
            multiplier += 0.15

        trump_score *= multiplier

        max_possible_score = (trump_ranks["right"] + trump_ranks["left"] + trump_ranks["A"] + trump_ranks["K"] + trump_ranks["Q"]) * 1.7

        return min(1.0, trump_score / max_possible_score)

    def evaluate_aces(self, hand, trump_suit):
        """
        Evaluates the strength of the aces in the hand by adding 1 per ace and normalizing to 0-1
        """
        # TODO: Add evaluation for doubletons (Kx, Qx) as those should be evaluated differently (could become sorta like aces)
        # TODO: King could be a boss card (basically an Ace) if an ace was the up card and turned down
        aces_sum = 0
        num_aces = 0

        trump_cards = self.get_trump_cards(hand, trump_suit)
        non_trump_cards = [card for card in hand if card not in trump_cards]

        suit_counts = {}
        for card in non_trump_cards:
            if card.suit not in suit_counts:
                suit_counts[card.suit] = 0
            suit_counts[card.suit] += 1

        for card in non_trump_cards:
            if card.rank == "A":
                num_aces += 1
                base_score = 0.9 if card.suit == self.SUIT_PAIRS[trump_suit] else 1

                if suit_counts[card.suit] == 1:
                    multiplier = 1
                elif suit_counts[card.suit] == 2:
                    multiplier = 0.9
                elif suit_counts[card.suit] == 3:
                    multiplier = 0.7
                else:
                    multiplier = 0.5

                aces_sum += base_score * multiplier

        # Aces are more valuable if you have a lot of trump
        bonus = 1.0
        num_non_trump_suits = len(suit_counts)
        if len(trump_cards) >= 3 and num_aces >= 1:
            bonus += 0.2
            if num_non_trump_suits == 1:
                bonus += 0.1

        aces_sum *= bonus

        max_possible_score = 2.9
        return min(1, aces_sum / max_possible_score) # Normalize value to 0-1 

    def evaluate_voids(self, hand, trump_suit):
        """
        Evaluates the strength of the suit voids in the hand by counting the number of suits that are not in the hand and normalizing to 0-1
        """

        trump_cards = self.get_trump_cards(hand, trump_suit)

        if len(trump_cards) == 0:
            # Voids are not valuable if you have no trump cards
            return 0

        non_trump_cards = [card for card in hand if card not in trump_cards]
        non_trump_suits = set(card.suit for card in non_trump_cards)
        num_non_trump_suits = len(non_trump_suits)

        if num_non_trump_suits == 0:
            # Only have trump cards
            return 1.0
        elif num_non_trump_suits == 1:
            # Only trump and one other suit, stronger if you have more trump cards
            return 1.0 if len(trump_cards) == 3 else 0.9
        elif num_non_trump_suits == 2:
            # Have one void
            return 0.15

        # Have all suits
        return 0
        
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

    def determine_best_card(self, hand, trump_suit, played_cards, previous_tricks, trump_caller, going_alone, tricks_won):
        """
        Determines the best card to play in a trick
        """

        if len(hand) == 1:
            return hand[0]

        partner_called_trump = trump_caller.name == self.partner
        player_called_trump = trump_caller.name == self.name
        opponent_called_trump = not partner_called_trump and not player_called_trump # TODO: It can be useful to know which opponent called trump specifically as that can change the card to play
        player_going_alone = going_alone and player_called_trump

        # Check if you are leading
        if not played_cards:
            # Decide what card to lead
            return self.choose_lead_card(hand, trump_suit, previous_tricks, partner_called_trump, player_called_trump, opponent_called_trump, player_going_alone, tricks_won)
        
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
        lowest_card = self.get_worst_card(hand, trump_suit)

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
                # Cannot win trick, so play lowest card
                return lowest_card 

    def choose_lead_card(self, hand, trump_suit, previous_tricks, partner_called_trump, player_called_trump, opponent_called_trump, player_going_alone, tricks_won):
        """
        Determines the best card to lead with
        """
        trump_cards = self.get_trump_cards(hand, trump_suit)

        # Get all cards that are the highest card in the suit remaining
        boss_cards = self.get_boss_cards_in_hand(hand, previous_tricks, trump_suit)
        non_trump_boss = [card for card in boss_cards if card.suit != trump_suit and not card.is_left_bower(trump_suit)]
        offsuit_cards = [card for card in hand if card.suit != trump_suit and not card.is_left_bower(trump_suit)]
        have_highest_trump = self.has_boss_card(hand, trump_suit, previous_tricks, trump_suit)
        trump_was_led_previously = any((trick_cards[0].card.suit == trump_suit or trick_cards[0].card.is_left_bower(trump_suit)) for trick_cards in previous_tricks.values())
        secured_point = tricks_won >= 3

        # If you have highest trump card and a offsuit boss card, lead the trump then the boss card
        if have_highest_trump and non_trump_boss:
            if player_called_trump or partner_called_trump or (opponent_called_trump and trump_was_led_previously):
                return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
        
        # On second to last trick, if you have one trump and one offsuit, lead the offsuit if you called it
        if len(previous_tricks) == 3 and len(hand) == 2:
            if len(trump_cards) == 1:
                if player_going_alone and secured_point:
                    return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit)) # TODO: Need to know if we have 3 tricks or not (guaranteed to not get euchred so can play more aggressively)
                return min(hand, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # Lead strong if partner called trump
        if partner_called_trump and trump_cards:
            # Do not lead a trump card if trump has already been led in a previous trick unless you have a strong hand
            if not trump_was_led_previously or (len(trump_cards) > 1 and non_trump_boss):
                return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # If you called trump and have highest trump, lead it
        if player_called_trump:
            if have_highest_trump:
                return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            elif len(trump_cards) > 1:
                if player_going_alone:
                    return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
                return min(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            elif player_going_alone:
                return max(offsuit_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # If opponents called, but you have a strong hand, lead trump
        if opponent_called_trump:
            if non_trump_boss and len(trump_cards) >= 3:
                if have_highest_trump:
                    return max(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
                else:
                    return min(trump_cards, key=lambda x: BotLogic.euchre_rank(x, trump_suit))
            
        # Lead highest off suit if it is a boss card
        if non_trump_boss:
            return max(non_trump_boss, key=lambda x: BotLogic.euchre_rank(x, trump_suit))

        # Otherwise, create void if possible or lead lowest card
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