$(document).ready(function () {
    $("#start-game-button").click(function () {
        $.ajax({
            url: "/start-game/", // Matches the URL in urls.py
            type: "POST",
            success: function (response) {
                // Map cards to their positions
                const positions = {
                    "Player": "#human-card",
                    "Opponent1": "#bot1-card",
                    "Team Mate": "#bot2-card",
                    "Opponent2": "#bot3-card",
                };

                // Update the DOM with the dealt cards
                for (let player in response.dealt_cards) {
                    $(positions[player]).text(response.dealt_cards[player]); // Show card text
                }

                // Clear any existing dealer icons
                $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();

                // Add the dealer icon to the corresponding rectangle
                const dealerPosition = positions[response.dealer];
                $(dealerPosition).addClass("dealer-highlight"); // Optional styling
                $(dealerPosition).prepend(`
                    <img src="/static/images/dealer-icon.jpg" alt="Dealer Icon" class="dealer-icon">
                `);

                // Update modal content and store the dealer's name
                dealer = response.dealer;
                $("#modal-dealer .modal-content").html(
                    `<p><strong>Highest Card:</strong> ${response.highest_card}</p>
                     <p><strong>Dealer:</strong> ${response.dealer}</p>`
                );

                // Display the modal
                $("#modal-dealer").fadeIn();
            },
            error: function (xhr) {
                alert("An error occurred: " + xhr.responseText);
            }
        });
    });

    // When you close the choose dealer modal, deal cards to each player
    $("#modal-ok-button").click(function () {
        // Hide the modal
        $("#modal-dealer").fadeOut();

        // Clear the rectangles 
        $(".rectangle").not(".center").text("");

        // Request a new hand to be dealt
        $.ajax({
            url: "/deal-hand/", // New endpoint for dealing a hand
            type: "POST",
            data: { dealer: dealer }, // Pass the dealer's name
            success: function (response) {
                // Map cards to their positions
                const positions = {
                    "Player": "#human-card",
                    "Opponent1": "#bot1-card",
                    "Team Mate": "#bot2-card",
                    "Opponent2": "#bot3-card",
                };

                // Display the dealt hand in each rectangle
                for (let player in response.hands) {
                    const cards = response.hands[player].join(", "); // Combine cards into a single string
                    const playerRectangle = $(positions[player]);
                    playerRectangle.text(cards);

                    // Add the dealer icon to the dealer's rectangle
                    if (player === dealer) {
                        playerRectangle.prepend(`
                            <img src="/static/images/dealer-icon.jpg" alt="Dealer Icon" class="dealer-icon">
                        `);
                    }
                }
            },
            error: function (xhr) {
                alert("An error occurred while dealing the hand: " + xhr.responseText);
            }
        });
    });
});

// Close dialogs when ok button is clicked
// $(document).ready(function () {
//     $("#modal-ok-button").click(function () {
//         $("#modal-dealer").modal('hide'); // Close the modal
//     });
// });