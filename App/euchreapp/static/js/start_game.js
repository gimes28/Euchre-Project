$(document).ready(function () {
    let trumpCard = null;
    let currentPlayerIndex = 0;
    let playerOrder = [];
    let currentSuit = "";
    let trumpSelected = false;

    // Map cards to their positions
    const positions = {
        "Player": "#human-card",
        "Opponent1": "#bot1-card",
        "Team Mate": "#bot2-card",
        "Opponent2": "#bot3-card",
    };

    // Function to display the trump card modal
    function showTrumpCardDialog(card, player) {
        trumpCard = card; // Ensure the current trump card is updated
        $("#modal-trump .modal-content").html(`
            <p><strong>Trump Card:</strong> ${card}</p>
            <p><strong>${player}</strong>, do you want to make this the trump card?</p>
        `);
        $("#accept-trump-button").show();
        $("#reject-trump-button").show();
        $("#ok-trump-button").hide();
        $("#modal-trump").fadeIn();
    }

    // Function to display the final message
    function showFinalMessage(message) {
        $("#modal-trump .modal-content").html(`
            <p>${message}</p>
        `);
        $("#accept-trump-button").hide();
        $("#reject-trump-button").hide();
        $("#ok-trump-button").show();
    }

    // Start the game
    $("#start-game-button").click(function () {
        $.ajax({
            url: "/start-game/", // Matches the URL in urls.py
            type: "POST",
            success: function (response) {
                // Display the dealt cards
                for (let player in response.dealt_cards) {
                    $(positions[player]).text(response.dealt_cards[player]);
                }

                // Highlight the dealer
                $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();
                const dealerPosition = positions[response.dealer];
                $(dealerPosition).addClass("dealer-highlight");
                $(dealerPosition).prepend(`
                    <img src="/static/images/dealer-icon.jpg" alt="Dealer Icon" class="dealer-icon">
                `);

                // Show dealer modal
                dealer = response.dealer;
                $("#modal-dealer .modal-content").html(`
                    <p><strong>Highest Card:</strong> ${response.highest_card}</p>
                    <p><strong>Dealer:</strong> ${response.dealer}</p>
                `);
                $("#modal-dealer").fadeIn();

                // Set player order for trump selection
                playerOrder = response.player_order;
            },
            error: function (xhr) {
                alert("An error occurred: " + xhr.responseText);
            }
        });
    });

    // Deal cards after selecting the dealer
    $("#modal-ok-button").click(function () {
        $("#modal-dealer").fadeOut();

        // Deal 5 cards to each player
        $.ajax({
            url: "/deal-hand/",
            type: "POST",
            data: { dealer: dealer },
            success: function (response) {
                for (let player in response.hands) {
                    const cards = response.hands[player].join(", ");
                    $(positions[player]).text(cards);

                    // Highlight the dealer
                    if (player === dealer) {
                        $(positions[player]).prepend(`
                            <img src="/static/images/dealer-icon.jpg" alt="Dealer Icon" class="dealer-icon">
                        `);
                    }
                }

                // Start the trump card selection process
                const initialTrumpCard = response.remaining_cards[0];
                showTrumpCardDialog(initialTrumpCard, playerOrder[currentPlayerIndex]);
            },
            error: function (xhr) {
                alert("An error occurred while dealing the hand: " + xhr.responseText);
            }
        });
    });

    // Handle accepting the trump card
    $("#accept-trump-button").click(function () {
        const currentPlayer = playerOrder[currentPlayerIndex];

        $.ajax({
            url: "/accept-trump/",
            type: "POST",
            data: { player: currentPlayer, card: trumpCard },
            success: function (response) {
                trumpSelected = true;
                currentSuit = response.trump_suit;

                // Update the current trump suit text and add the suit image
                const suitImageMap = {
                    "spades": "/static/images/spade.png",
                    "hearts": "/static/images/heart.png",
                    "diamonds": "/static/images/diamond.png",
                    "clubs": "/static/images/club.png"
                };

                const suitImagePath = suitImageMap[currentSuit];
                $(".bottom-left-column-1").html(`
                    <span>Current Trump</span>
                    <div class="icon-wrapper">
                        <img src="${suitImagePath}" alt="${currentSuit}" class="trump-suit-icon">
                    </div>
                `);

                // Update the player's hand in their rectangle
                const updatedHand = response.updated_hand.join(", ");
                $(positions[currentPlayer]).text(updatedHand);

                // Show the final message
                showFinalMessage(`${currentPlayer} accepted the trump card!`);
            },
            error: function (xhr) {
                alert("An error occurred while accepting the trump card: " + xhr.responseText);
            }
        });
    });

    // Handle rejecting the trump card
    $("#reject-trump-button").click(function () {
        currentPlayerIndex++;
        if (currentPlayerIndex < playerOrder.length) {
            // Get the next trump card
            const nextTrumpCard = trumpCard; // Update dynamically if backend rotates trump card
            showTrumpCardDialog(nextTrumpCard, playerOrder[currentPlayerIndex]);
        } else {
            showFinalMessage("No one accepted the trump card.");
        }
    });

    // Handle the OK button to close the trump card modal
    $("#ok-trump-button").click(function () {
        $("#modal-trump").fadeOut();
    });

    // Reset the game when the page loads
    $.ajax({
        url: "/reset-game/", // URL for the reset endpoint
        type: "POST",
        success: function (response) {
            console.log(response.message); // Log success message
        },
        error: function (xhr) {
            console.error("An error occurred while resetting the game: " + xhr.responseText);
        }
    });

    window.addEventListener("beforeunload", function () {
        $.ajax({
            url: "/reset-game/",
            type: "POST",
            async: false // Synchronous request to ensure the reset completes
        });
    });
});