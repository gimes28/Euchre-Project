class BotLogic:
    def determine_trump(self, hand, dealer, up_card, trump_round, player_order):
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

        """

        print("hand: ", hand)
        print("dealer: ", dealer)
        print("up_card: ", up_card)
        print("trump_round: ", trump_round)
        print("player_order: ", player_order)

        if trump_round == 1:
            # First round
            up_card_rank, trump_suit = up_card.split(" of ")
            left_bower_suit = "clubs" if trump_suit == "spades" else \
                            "spades" if trump_suit == "clubs" else \
                            "diamonds" if trump_suit == "hearts" else "hearts"
            trump_cards = [playedCard for playedCard in hand if (playedCard.card.suit == trump_suit) or (playedCard.card.rank == "J" and playedCard.card.suit == left_bower_suit)]
            num_trump_cards = len(trump_cards)

            num_aces = len([playedCard for playedCard in hand if playedCard.card.rank == "A"])
            
            if num_trump_cards + num_aces >= 4:
                # ORDER UP (4 trumps is automatic order up and aces are almost as valuable as trumps)
                return trump_suit

            # Count number of suits
            suits = []
            for playedCard in hand:
                if playedCard.card.suit not in suits:
                    suits.append(playedCard.card.suit)
            num_suits = len(suits)

            if (num_trump_cards >= 3 and num_suits <= 2):
                # ORDER UP (3 trump 2 suited is automatic order up)
                return trump_suit

        return 'pass' # Hand not strong enough to call trump

    def determine_best_card(self, hand, trump_suit, played_cards):
        # Returns the card that the bot should play
        
        pass 