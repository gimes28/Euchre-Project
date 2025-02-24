class BotLogic:
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
            left_bower_suit = "clubs" if trump_suit == "spades" else \
                            "spades" if trump_suit == "clubs" else \
                            "diamonds" if trump_suit == "hearts" else "hearts"
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

            print("Dealer? ", player_name, dealer)
            # Dealer has to choose suit
            if player_name == dealer:
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

    def determine_best_card(self, hand, trump_suit, played_cards):
        # Returns the card that the bot should play
        
        pass 