// tooltip messages, id on the left, message on the right //

const tooltips = {
    "kitty": `
        <strong>What is the Kitty?</strong><br><br>
        The <em>Kitty</em> is a set of <strong>4 leftover cards</strong> after the deal.<br><br>
        - The top card is revealed and may be picked up by the dealer if it's chosen as Trump.<br>
        - If no one chooses the revealed card, players will get a second chance to call a trump suit.<br>
        - The remaining Kitty cards stay hidden unless revealed after the round.<br><br>
        <strong>Strategy Tip:</strong> Pay attention to the Kitty — it can influence which suit becomes trump!
    `,

    "dealer": `
        <strong>How is the Dealer Chosen?</strong><br><br>
        - At the start of the game, all players draw one card.<br>
        - The player who draws the <strong>highest card</strong> becomes the first dealer.<br><br>
        <strong>After the first round:</strong><br>
        - The role of dealer rotates to the left after each round.<br><br>
        <strong>Visual Tip:</strong> Look for the <img src="/static/images/dealer-icon.png" alt="Dealer Icon" style="width: 16px; vertical-align: middle;"> icon and player highlighted in red to find the current dealer.
    `,

    "trump": `
        <strong>Understanding the Trump Suit</strong><br><br>
        The Trump suit is the <strong>dominant suit</strong> for the round. It beats all other suits.<br><br>
        <strong>Trump Hierarchy (highest to lowest):</strong><br>
        - Right Bower: Jack of the trump suit<br>
        - Left Bower: Jack of the same color (non-trump) suit<br>
        - Trump suit cards (A, K, Q, 10, 9)<br>
        - Non-trump cards follow their own rank<br><br>
        <strong>Strategy Tip:</strong> Trump cards can win a trick even if they're not the first suit played.
    `,

    "score": `
        <strong>How to score points in Euchre:</strong><br><br>

        <strong>1. Scoring as the Makers (the team that calls the trump suit):</strong><br>
        - Win 3 or 4 tricks → 1 point<br>
        - Win all 5 tricks ("sweep") → 2 points<br>
        - Go alone and win all 5 → 4 points<br><br>

        <strong>2. Scoring as the Defenders (the team that didn't call the trump suit):</strong><br>
        - Euchre the makers (stop them from taking 3 tricks) → 2 points<br><br>

        <strong>3. Game End:</strong><br>
        - First team to reach 10 or 11 points wins the game
    `,

    "tricks": `
        <strong>What is a Trick?</strong><br><br>
        A Trick is when each player plays <strong>one card</strong> during a turn.<br><br>
        - The highest card (following the rules of suit and trump) wins the trick.<br>
        - There are 5 tricks per round — and each one counts!<br><br>
        <strong>Winning Tips:</strong><br>
        - Always follow suit if you can.<br>
        - Use Trump wisely — especially late in a round when it matters most.
    `
};
