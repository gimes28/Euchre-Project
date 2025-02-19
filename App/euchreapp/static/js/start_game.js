$(document).ready(function () {
    let currentPlayerIndex = 0;
    let playerOrder = [];
    let currentSuit = "";
    let trumpSelected = false;
    let gameResponse = null; // Store the global response object here

    // Reset Current Trump and Game Score on Page Load
    $("#current-trump").text("None");
    $("#game-score").text("Team 1: 0 | Team 2: 0");


    // Map cards to their positions
    const positions = {
        "Player": "#human-card",
        "Opponent1": "#bot1-card",
        "Team Mate": "#bot2-card",
        "Opponent2": "#bot3-card",
    };

    // Function to display the trump card modal
    function showTrumpCardDialog(card, player) {
        $("#start-game-button").hide();
        $("#ok-round-button").hide();
        $("#modal-round").fadeOut();
        $("#modal-dealer").fadeOut();
        $("#reject-trump-button").show();
        $("#accept-trump-button").show();
        $(".suit-button").hide();
        $("#modal-trump .modal-content").html(`
            <p><strong>Trump Card:</strong> ${card}</p>
            <p><strong>${player}</strong>, do you want to make this the trump card?</p>
        `);

        $("#reject-trump-button").prop("disabled", false);
    
        // Ensure buttons are properly assigned new handlers
        $("#accept-trump-button").off("click").on("click", function () {
            $("#modal-trump").fadeOut(); // Hide the modal before proceeding
            acceptTrump(player, card, 1);
        });
    
        $("#reject-trump-button").off("click").on("click", function () {
            $("#modal-trump").fadeOut(); // Hide modal before moving to the next player
            rejectTrump(player, 1);
        });
    
        $("#modal-trump").fadeIn(); // Ensure modal appears properly
    }    
    
    // Function to display the trump card modal for the 2nd round of trump selection
    function showTrumpCardDialog2ndRound(upCardSuit, player) {
        $("#start-game-button").hide();
        $("#ok-round-button").hide();
        $("#modal-round").fadeOut();
        $("#modal-dealer").fadeOut();
        $("#reject-trump-button").show();
        $("#accept-trump-button").hide();
        $(".suit-button").show();
        $("#modal-trump .modal-content").html(`
            <p><strong>${player}</strong>, select a trump suit or pass:</p>
        `);

        // Enable all suit buttons
        $(".suit-button").prop("disabled", false);
        $("#reject-trump-button").prop("disabled", false);

        // Disable the button for the upcard suit
        $(`.suit-button[data-suit="${upCardSuit}"]`).prop("disabled", true);

        // Disable the pass button if player is the dealer
        if (player === dealer) {
            $("#reject-trump-button").prop("disabled", true);
        }

        $(".suit-button").off("click").on("click", function () {
            const selectedSuit = $(this).data("suit");
            $("#modal-trump").fadeOut(); // Hide the modal before proceeding
            acceptTrump(player, selectedSuit, 2);
        });

        $("#reject-trump-button").off("click").on("click", function () {
            $("#modal-trump").fadeOut();
            rejectTrump(player, 2);
        });

        $("#modal-trump").fadeIn(); // Ensure modal appears properly
    }    

    function acceptTrump(player, card, trumpRound) {
        const data = { player: dealer, trump_round: trumpRound };

        if (trumpRound === 1) {
            data.card = card;
        } else if (trumpRound === 2) {
            data.suit = card; // The card is actually the selected suit
        }
        trumpRound = 1; // Reset the trump round to 1 after accepting trump

        $.ajax({
            url: "/accept-trump/",
            type: "POST",
            data: data,
            success: function (response) {
                trumpSelected = true;
                currentSuit = response.trump_suit;
    
                // Update UI with the new trump suit
                updateTrumpDisplay(response.trump_suit);
                // displayHumanHand(response.updated_hand);
    
                // Hide trump modal and show round start confirmation
                $("#modal-trump").fadeOut();
                showRoundStart(`${player} accepted trump! The trump suit is now ${currentSuit}.`);
            },
            error: function (xhr) {
                alert("Error accepting trump: " + xhr.responseText);
            }
        });
    }
    
    function rejectTrump(player, trumpRound) {
        currentPlayerIndex++;
    
        if (currentPlayerIndex < playerOrder.length) {
            if (trumpRound === 1) {
                setTimeout(() => {
                if (playerOrder[currentPlayerIndex].is_human == true) {
                    showTrumpCardDialog(gameResponse.remaining_cards[0], playerOrder[currentPlayerIndex].name);
                } else {
                    determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], trumpRound);
                }
            }, 400); // Delay prevents modal flickering
            } else if (trumpRound === 2) {
                setTimeout(() => {
                    if (playerOrder[currentPlayerIndex].is_human == true) {
                        showTrumpCardDialog2ndRound(gameResponse.remaining_cards[0].split(" of ")[1], playerOrder[currentPlayerIndex].name);
                    } else {
                        determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], trumpRound);
                    }
                }, 400); // Delay prevents modal flickering
            }
        } else {
            // Everyone passed in first round, so start second round
            trumpRound = 2;
            currentPlayerIndex = 0;
            
            // Give trump dialog box, but this time player can select any suit except for the upCardSuit
            setTimeout(() => {
                showTrumpCardDialog2ndRound(gameResponse.remaining_cards[0].split(" of ")[1], playerOrder[currentPlayerIndex].name);
            }, 400);
        }
    }

    function determineBotTrumpDecision(player, upCard, trumpRound) {
        $.ajax({
            url: "/determine-trump/",
            type: "POST",
            data: {
                player: player,
                dealer: dealer,
                up_card: upCard,
                trumpRound: trumpRound,
                player_order: playerOrder
            },
            async: false,
            success: function (response) {
                const botDecision = response.decision;
                console.log("Bot decision:", botDecision);

                if (trumpRound === 1) {
                    if (botDecision === 'pass') {
                        rejectTrump(player, trumpRound);
                    } else {
                        acceptTrump(player, upCard, trumpRound);
                    }
                } else if (trumpRound === 2) {
                    if (botDecision === 'pass') {
                        rejectTrump(player, trumpRound);
                    } else {
                        acceptTrump(player, botDecision, trumpRound);
                    }
                }
            },
            error: function (xhr) {
                alert("Error determining bot decision: " + xhr.responseText);
            }
        });
    }

    // Function to display the final message before round starts
    function showFinalMessage(message) {
        $("#modal-trump .modal-content").html(`
            <p>${message}</p>
        `);
    
        // Hide unnecessary buttons
        $("#accept-trump-button").hide();
        $("#reject-trump-button").hide();
        $("#ok-modal-button").hide();
        $("#modal-round-button").hide();
        $("#ok-trump-button").show();  // Ensure OK button is visible
    
        $("#modal-trump").fadeIn(); // Ensure modal is visible
    }

    // Function to display the round status
    function showRoundStart(message) {
        $("#modal-trump").fadeOut(); // Hide trump modal if still visible
    
        $("#modal-round .modal-content").html(`
            <p>${message}</p>
            <p><strong>Order of Play:</strong> ${playerOrder.map(player => player.name).join(", ")}</p>
        `);

        // Hide unnecessary buttons
        $("#accept-trump-button").hide();
        $("#reject-trump-button").hide();
        $("#ok-modal-button").hide();
        $("#modal-round-button").show();
        $("#ok-trump-button").hide();

        $("#modal-round").fadeIn(); // Ensure round modal is displayed
    }
    

    // Start the game
    $("#start-game-button").click(function () {
        $.ajax({
            url: "/start-game/", // Matches the URL in urls.py
            type: "POST",
            success: function (response) {

                // Deal hands AFTER the game has started
                $.ajax({
                    url: "/deal-hand/",
                    type: "POST",
                    success: function (response) {
                        if (response.hands && response.hands["Player"]) {
                            // displayHumanHand(response.hands["Player"]);
                        }
                    }
                });

                // Fetch and update the game score AFTER starting the game
                $.ajax({
                    url: "/get-game-score/",
                    type: "GET",
                    success: function(response) {
                        updateGameScore(response.team1, response.team2);
                    },
                    error: function(xhr) {
                        console.error("Error fetching game score:", xhr.responseText);
                    }
                });

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

                initializeDealerModal(response);

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
                gameResponse = response;
                playerOrder = response.player_order; // Update player order
                currentPlayerIndex = 0;
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
                if (playerOrder[currentPlayerIndex].is_human == true) {
                    showTrumpCardDialog(response.remaining_cards[0], playerOrder[currentPlayerIndex].name);
                } else {
                    determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], 1);
                }
            },
            error: function (xhr) {
                alert("An error occurred while dealing the hand: " + xhr.responseText);
            }
        });
    });

    function displayDealtCards(response) {
        for (let player in response.hands) {
            const cards = response.hands[player].join(", ");
            $(positions[player]).text(cards);
        }
    }

    function initializeDealerModal(response) {
        dealer = response.dealer;
        $("#modal-dealer .modal-content").html(`
            <p><strong>Highest Card:</strong> ${response.highest_card}</p>
            <p><strong>Dealer:</strong> ${response.dealer}</p>
        `);
        $("#modal-dealer").fadeIn();
    }

    // Handle rejecting the trump card
    $("#reject-trump-button").click(function () {
        currentPlayerIndex++;
        if (currentPlayerIndex <= 3) {
            if (playerOrder[currentPlayerIndex].is_human == true) {
                showTrumpCardDialog(gameResponse.remaining_cards[0], playerOrder[currentPlayerIndex].name);
            } else {
                determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], 1);
            }
        } else {
            showFinalMessage("No one accepted the trump card.");
            trumpSelected = false;
        }
    });

    // Function to reset the UI when trump selection starts
    function resetPlayerHandBeforeTrump() {
        $("#player-hand").empty(); // Clear displayed cards to prevent double-counting
    }

    // Handle accepting the trump card
    $("#accept-trump-button").click(function () {
        resetPlayerHandBeforeTrump(); // Ensure UI is clear before updating
        
        const currentPlayer = playerOrder[currentPlayerIndex];

        $.ajax({
            url: "/accept-trump/",
            type: "POST",
            data: { player: currentPlayer, card: gameResponse.remaining_cards[0] },
            success: function (response) {
                trumpSelected = true;
                currentSuit = response.trump_suit;

                // Update the trump suit display
                updateTrumpDisplay(response.trump_suit);

                // Update the player's hand in their rectangle
                // displayHumanHand(response.updated_hand);

                // Show the final message
                showFinalMessage(`${currentPlayer} accepted the trump card!`);
            },
            error: function (xhr) {
                alert("An error occurred while accepting the trump card: " + xhr.responseText);
            }
        });
    });

    function updateTrumpDisplay(suit) {
        const suitImageMap = {
            "spades": "/static/images/spade.png",
            "hearts": "/static/images/heart.png",
            "diamonds": "/static/images/diamond.png",
            "clubs": "/static/images/club.png"
        };

        const suitImagePath = suitImageMap[suit];
        $(".bottom-left-column-1").html(`
            <span>Current Trump</span>
            <div class="icon-wrapper">
                <img src="${suitImagePath}" alt="${suit}" class="trump-suit-icon">
            </div>
        `);
    }


    // Handle the OK button to close the trump card modal and open the round start model
    $("#ok-trump-button").click(function () {
        $("#modal-trump").fadeOut();
        $("#mok-trump-button").hide();
        $("#modal-round").fadeIn();
        if (trumpSelected) {
            showRoundStart(`Trump suit for round: ${currentSuit}!`);
        } else {
            showRoundStart("The first card played will set the trump suit.");
        }
    });    

    // Function to display human player's hand as clickable buttons
    // function displayHumanHand(cards) {
    //     $("#player-hand").empty();

    //     cards.forEach(card => {
    //         let cardButton = `<button class="card-btn" data-card="${card}">${card}</button>`;
    //         $("#player-hand").append(cardButton);
    //     });

    //     // When player clicks a card, send to backend
    //     $(".card-btn").click(function () {
    //         let selectedCard = $(this).attr("data-card");
    //         playSelectedCard(selectedCard);
    //     });
    // }
    
    // // After dealing hands, show player's hand
    // $.ajax({
    //     url: "/deal-hand/",
    //     type: "POST",
    //     success: function (response) {
    //         if (response.hands && response.hands["Player"]) {
    //             displayHumanHand(response.hands["Player"]); // Show player's hand
    //         }
    //     }
    // });

    // Function to show the round results modal
    function showRoundResults(results) {
        let winningMessage = results.winning_team
            ? `<p><strong>${results.winning_team} won the game!</strong></p>`
            : `<p>Current Score - Team 1: ${results.team1_points} | Team 2: ${results.team2_points}</p>`;

        // Update game score display
        updateGameScore(results.team1_points, results.team2_points);

        // Remove trump suit icon
        $("#current-trump").text("None");
    
        $("#modal-round .modal-content").html(`
            <p><strong>Round Completed!</strong></p>
            ${winningMessage}
        `);
    
        $("#modal-round-button").hide(); // Hide Start Round button
    
        if (results.winning_team) {
            $("#ok-round-button").hide();
            $("#end-game-button").show();  // Show End Game button
        } else {
            $("#ok-round-button").show();
            $("#end-game-button").hide();
        }
    
        $("#modal-round").fadeIn();  // Ensure modal is displayed
    }
    

    // Handle starting the round
    $("#modal-round-button").click(function (event) {
        event.preventDefault();
        $("#modal-round").fadeOut();
    
        $.ajax({
            url: "/start-round/",
            type: "POST",
            success: function (response) {
                console.log("Round Results Received:", response);
    
                if (response.error) {
                    alert("Error: " + response.error);
                    return;
                }
    
                if (response.tricks) {
                    updatePreviousTricks(response.tricks);  // Update all tricks at once
                }
    
                if (response.round_results) {
                    finalizeRound(response);
                }
    
                updateRemainingCards(); // Refresh remaining cards
            },
            error: function (xhr) {
                alert("Error starting round: " + xhr.responseText);
            }
        });
    });
    
    
    

    // OK button to close round results modal, and start next round trump selection
    $("#ok-round-button").click(function () {
        $("#modal-round").fadeOut();  // Hide the round results modal

        $.ajax({
            url: "/deal-next-hand/",  // Redeal hands and rotate dealer
            type: "POST",
            success: function (response) {

                // Fetch updated game score
                $.ajax({
                    url: "/get-game-score/",
                    type: "GET",
                    success: function(response) {
                        updateGameScore(response.team1, response.team2);
                    },
                    error: function(xhr) {
                        console.error("Error fetching game score:", xhr.responseText);
                    }
                });

                console.log("New hands dealt:", response);

                // Save response for later reference
                gameResponse = response;
                currentPlayerIndex = 0;
                playerOrder = response.player_order;

                // ✅ Clear previous dealer icon before setting new dealer
                $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();

                // ✅ Highlight the new dealer
                if (response.dealer && positions[response.dealer]) {
                    const dealerPosition = positions[response.dealer];
                    $(dealerPosition).addClass("dealer-highlight");
                    $(dealerPosition).prepend(`
                        <img src="/static/images/dealer-icon.jpg" alt="Dealer Icon" class="dealer-icon">
                    `);
                } else {
                    console.error("Error: Dealer position not found in UI.");
                }

                // Update UI with new hands
                displayDealtCards(response);
                //initializeDealerModal(response);

                // 🔥 Start trump selection process with the first trump card
                if (response.remaining_cards.length > 0) {
                    if (playerOrder[currentPlayerIndex].is_human == true) {
                        showTrumpCardDialog(response.remaining_cards[0], playerOrder[currentPlayerIndex].name);
                    } else {
                        determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], 1);
                    }
                } else {
                    console.error("Error: No remaining cards for trump selection!");
                }
            },
            error: function (xhr) {
                alert("An error occurred while dealing the next hand: " + xhr.responseText);
            }
        });
    });


    // End game when one team reaches the points to win
    $("#end-game-button").click(function () {
        $.ajax({
            url: "/reset-game/",  // Reset the game state
            type: "POST",
            success: function (response) {
                console.log(response.message);
                // Reset Current Trump and Game Score on Page Load
                $("#current-trump").text("None");
                $("#game-score").text("Team 1: 0 | Team 2: 0");
    
                // Close all modals and reset the UI
                $(".custom-modal").fadeOut();
                $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();
                
                // Show the Start Game button again
                $("#end-game-button").hide();
                $("#start-game-button").show();
            },
            error: function (xhr) {
                alert("Error ending the game: " + xhr.responseText);
            }
        });
    });
    
    
    

    // Function to update game score
    function updateGameScore(team1, team2) {
        $(".bottom-left-column-2").html(`
            <span>Game Score</span>
            <p>Team 1: ${team1} points</p>
            <p>Team 2: ${team2} points</p>
        `);
    }

    function updateRemainingCards() {
        $.ajax({
            url: "/get-remaining-cards/",
            type: "GET",
            success: function (response) {
                if (response.remaining_cards) {
                    $("#remaining-cards-list").html(
                        response.remaining_cards.map(card => `<p>${card}</p>`).join("")
                    );
                } else {
                    $("#remaining-cards-list").html("<p>No cards remaining.</p>");
                }
            },
            error: function (xhr) {
                console.error("Error fetching remaining cards:", xhr.responseText);
                $("#remaining-cards-list").html("<p>Error loading remaining cards.</p>");
            }
        });
    }

    function updatePreviousTricks(tricks) {
        let tricksTable = $("#previous-tricks-body");
        tricksTable.empty();  // Clear previous entries
    
        tricks.forEach(trickData => {
            let newRow = `
                <tr>
                    <td>${trickData.trick_number}</td>
                    <td>${trickData.players[0]}</td>
                    <td>${trickData.cards[0]}</td>
                    <td>${trickData.players[1]}</td>
                    <td>${trickData.cards[1]}</td>
                    <td>${trickData.players[2]}</td>
                    <td>${trickData.cards[2]}</td>
                    <td>${trickData.players[3]}</td>
                    <td>${trickData.cards[3]}</td>
                    <td>${trickData.winner}</td>
                </tr>
            `;
            tricksTable.append(newRow);
        });
    }
    
    
    function finalizeRound(response) {
        console.log("Finalizing round:", response);
    
        if (!response.round_results) {
            console.error("Error: No round results received!");
            return;
        }
    
        showRoundResults({
            "team1_points": response.round_results.team1_points,
            "team2_points": response.round_results.team2_points,
            "winning_team": response.round_results.winning_team,
        });
    
        console.log("✅ Round Completed! Displaying results.");
    }

    // // Reset the game when the page loads
    // $.ajax({
    //     url: "/reset-game/", // URL for the reset endpoint
    //     type: "POST",
    //     success: function (response) {
    //         console.log(response.message); // Log success message
    //     },
    //     error: function (xhr) {
    //         console.error("An error occurred while resetting the game: " + xhr.responseText);
    //     }
    // });

    // window.addEventListener("beforeunload", function () {
    //     $.ajax({
    //         url: "/reset-game/",
    //         type: "POST",
    //         async: false // Synchronous request to ensure the reset completes
    //     });
    // });
});