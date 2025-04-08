// Make game states global to make it easier to show/hide
window.gameState = {
    trumpSelected: false,
    roundStarted: false,
    awaitingCard: false
};

window.currentPlayerHand = [];  

$(document).ready(function () {
    let currentPlayerIndex = 0;
    let playerOrder = [];
    let currentSuit = "";
    let trumpSelected = false;
    let gameResponse = null;
    let kitty = [] // Store the global response object here

    // Reset Current Trump, Game Score, Play Card modal on Page Load
    $("#current-trump").text("None");
    $("#game-score").text("Player Team: 0 | Opponent Team: 0");
    $("#modal-trick-play").fadeOut();
    
    // Initialize Semantic UI checkbox
    $('.ui.toggle.checkbox').checkbox();

    // if (results.winning_team) {
    //     $("#ok-round-button").hide();
    //     $("#end-game-button").show();  // Show End Game button
    // } else {
    //     $("#ok-round-button").show();
    //     $("#end-game-button").hide();
    // }    

    // Drop zone handling
    const dropZone = document.getElementById("drop-zone");
    const playBtn = document.getElementById("play-card-button");

    // Map cards to their positions
    const positions = {
        "Player": "#human-card",
        "Opponent1": "#bot1-card",
        "Team Mate": "#bot2-card",
        "Opponent2": "#bot3-card",
    };

    window.getCardImage = function (card) {
        if (card === "Hidden") {
            return "/static/images/cards/back.png";
        }
    
        if (card.includes("_of_")) {
            return `/static/images/cards/${card}.png`;
        }
    
        let cardParts = card.split(" of ");
        if (cardParts.length !== 2) {
            console.error("❌ Invalid card format:", card);
            return "/static/images/cards/back.png";
        }
    
        let rank = cardParts[0].toLowerCase();
        let suit = cardParts[1].toLowerCase();
        return `/static/images/cards/${rank}_of_${suit}.png`;
    };

    function formatCardForDOM(cardStr) {
        return cardStr.toLowerCase().replace(/ /g, "_");
    }    

    function formatCardString(cardStr) {
        if (cardStr.includes("_of_")) {
            const [rank, suit] = cardStr.split("_of_");
            return `${rank.toUpperCase()} of ${suit.toLowerCase()}`;
        } else if (cardStr.includes(" of ")) {
            const [rank, suit] = cardStr.split(" of ");
            return `${rank.toUpperCase()} of ${suit.toLowerCase()}`;
        } else {
            console.error("Invalid card format:", cardStr);
            return cardStr;
        }
    }


    function capitalize(str) {
        if (!str || typeof str !== "string") return str;
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }    
    

    function removeCardFromPlayerHand(cardId, player) {
        console.log(`🧹 Attempting to remove ${cardId} from ${player}-card`);
    
        let containerId = "";
        if (player === "Player") containerId = "#human-card";
        else if (player === "Team Mate") containerId = "#bot2-card";
        else if (player === "Opponent1") containerId = "#bot1-card";
        else if (player === "Opponent2") containerId = "#bot3-card";
    
        const cardImg = $(`${containerId} img[data-card="${cardId}"]`);
        if (cardImg.length) {
            cardImg.remove();
            console.log(`✅ Removed ${cardId} from ${containerId}`);
        } else {
            console.warn(`⚠️ ${cardId} not found in ${containerId}`);
        }
    }
    

    window.showPlayCardModal = function (playedSoFar = []) {
        const modal = document.getElementById("modal-trick-play");
        $("#drop-zone").removeAttr("data-played-card");
        $("#drop-zone").html(`<p>Drop your card here</p>`);  // reset drop zone
        const playedCardsSection = $("#played-cards-list");
    
        playedCardsSection.empty();
        playedSoFar.forEach(({ player, card }) => {
            playedCardsSection.append(`<li><strong>${player}</strong> played ${card}</li>`);
        });
    
        $("#modal-trick-play").fadeIn();
    };


    function clearCenterTrick() {
        // These are the 4 placeholders in the middle
        document.getElementById("trick-player").innerHTML = "";
        document.getElementById("trick-opponent1").innerHTML = "";
        document.getElementById("trick-team-mate").innerHTML = "";
        document.getElementById("trick-opponent2").innerHTML = "";
    }


    function playTrickLoop() {
        console.log("🎯 Trick loop triggered. Action:", gameState.lastAction);
        console.log("👀 Current gameState:", gameState);
    
        // Prevent trick loop from triggering if a card is being selected
        if (gameState.awaitingCard) {
            console.warn("⏸️ Trick loop paused - awaiting human card.");
            return;
        }
    
        $.ajax({
            url: "/play-trick-step/",
            type: "GET",
            success: function(response) {
                console.log("🧠 Trick step response:", response);
            
                // ✅ Only remove human card if this step was from the human
                if (response.player === "Player") {
                    const formatted = response.card.toLowerCase().replace(/ /g, "_");
                    const humanCard = document.querySelector(`#human-card img[data-card="${formatted}"]`);
                    if (humanCard) {
                        humanCard.remove();
                        console.log(`✅ Removed player card ${formatted} from UI`);
                    } else {
                        console.warn(`⚠️ Could not find player card ${formatted} to remove`);
                    }
                }
            
                // 🎯 Follow-up: handle response actions
                if (response.action === "awaiting_player") {
                    console.log("🃏 Awaiting human card selection...");
                    gameState.awaitingCard = true;
                    showTrickModal(response);
                } 
                else if (response.action === "bot_played") {
                    console.log("📤 Bot card played by:", response.player);
                    updateBotCardUI(response.player, response.card);
                    console.log("Looking for card:", formatCardForDOM(response.card), "for", response.player);
                    setTimeout(playTrickLoop, 700);
                } 
                else if (response.action === "trick_completed") {
                    console.log("🏁 Trick completed:", response.trick);
                    updatePreviousTrick(response.trick);
                    response.trick.players.forEach((name, index) => {
                    const card = response.trick.cards[index];
                    updateBotCardUI(name, card);
                });
            
                    setTimeout(() => {
                        resetCenter();
                        playTrickLoop();
                    }, 1000);
                } 
                else if (response.action === "round_completed") {
                    updatePreviousTrick(response.trick);
                    finalizeRound(response);
                    gameState.awaitingCard = false;
                    return;
                } 
                else {
                    console.warn("⚠️ Unexpected action:", response);
                }
            },
            error: function(err) {
                console.error("❌ Error in trick step:", err);
            }
        });
    }    
    
    
    function displayDealtCards(response) {
        for (let player in response.hands) {
            const cardContainer = $(positions[player]);
            cardContainer.empty(); // Clear previous cards
    
            response.hands[player].forEach((card, index) => {
                let imgSrc = player === "Player" ? getCardImage(card) : getCardImage("Hidden");
                cardContainer.append(`<img src="${imgSrc}" class="playing-card" data-card="${formatCardForDOM(card)}" data-player="${player}">`);
            });
        }
    }

    function updateBotCardUI(playerName, cardName) {
        if (!playerName || typeof playerName !== "string" || !cardName || typeof cardName !== "string") {
            console.error("❌ Invalid inputs to updateBotCardUI:", { playerName, cardName });
            return;
        }
    
        const trickAreaId = `trick-${playerName.toLowerCase().replace(/\s+/g, "-")}`;
        const trickArea = document.getElementById(trickAreaId);
    
        if (!trickArea) {
            console.warn(`⚠️ No trick area found for ${trickAreaId}`);
            return;
        }
    
        const formatted = formatCardForDOM(cardName);  // now consistent!
        const cardImg = document.createElement("img");
        cardImg.src = `/static/images/cards/${formatted}.png`;
        cardImg.alt = cardName;
        cardImg.classList.add("played-card");
        cardImg.setAttribute("data-player", playerName);
        cardImg.setAttribute("data-card", formatted);
    
        trickArea.innerHTML = '';
        trickArea.appendChild(cardImg);
    
        // Remove card from bot hand
        const handAreaId = getBotCardContainerId(playerName);
        const handArea = document.getElementById(handAreaId);
        if (handArea) {
            const cardToRemove = handArea.querySelector(`img[data-card="${formatted}"]`);
            if (cardToRemove) {
                cardToRemove.remove();
                console.log(`✅ Removed ${formatted} from ${handAreaId}`);
            } else {
                console.warn(`⚠️ ${formatted} not found in ${handAreaId}`);
            }
        }
    
        console.log(`🃏 ${playerName} played ${cardName} → rendered in ${trickAreaId}`);
    }
    
    
    // Utility: maps player name to DOM ID
    function getBotCardContainerId(playerName) {
        const name = playerName.toLowerCase();
        if (name.includes("opponent1")) return "bot1-card";
        if (name.includes("team mate")) return "bot2-card";
        if (name.includes("opponent2")) return "bot3-card";
        return null;
    }      
    

    // Final placement after everything else is loaded
    window.showTrickModal = function (data) {
        const modal = document.getElementById("modal-trick-play");
        const dropZone = document.getElementById("drop-zone");
        $("#modal-trick-play").removeClass("hidden"); 
        $("#modal-trick-play").fadeIn();

        dropZone.innerHTML = "";  // Clear drop zone
        $("#drop-zone").html(`<p>Drop your card here</p>`);  // reset drop zone
        $("#drop-zone").removeAttr("data-played-card");
    
    
        // Handle dragover event
        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault(); // Allow drop
        });
    
        // Handle drop event
        dropZone.addEventListener("drop", function (e) {
            e.preventDefault();
        
            const rawCard = e.dataTransfer.getData("card");
            if (!rawCard) return;
        
            const formattedCard = rawCard.includes("_of_")
            ? rawCard.replace("_of_", " of ")
            : rawCard;
        
            if (!formattedCard.includes(" of ")) {
                console.error("❌ Invalid card format:", formattedCard);
                return;
            }
            
            const [rank, suit] = formattedCard.split(" of ");

            if (!rank || !suit) {
                console.error("❌ Invalid rank or suit:", formattedCard);
                return;
            }
        
            const img = document.createElement("img");
            if (!img) return;
            img.src = getCardImage(formattedCard);
            img.classList.add("card", "card-in-modal");
            img.setAttribute("data-rank", rank.trim());
            img.setAttribute("data-suit", suit.trim());
        
            dropZone.innerHTML = "";
            dropZone.appendChild(img);
            dropZone.setAttribute("data-played-card", formattedCard);
            playBtn.disabled = false;
        });
    };
    

    function displayHighCards(response) {
        // Display the dealt high cards
        for (let player in response.dealt_cards) {
            const cardContainer = $(positions[player]);
            cardContainer.empty(); // Clear previous cards
            let highcard = response.dealt_cards[player];
            //console.log(highcard)
            let imgSrc = getCardImage(highcard);
            cardContainer.append(`<img src="${imgSrc}" class="playing-card" data-card="${highcard}" data-player="${player}">`);
        }
    }

    // Function to display the trump card modal
    function showTrumpCardDialog(card, player) {
        $("#start-game-button").hide();
        $("#modal-trick-play").hide();
        $("#start-game-form").hide();
        $("#ok-round-button").hide();
        $("#modal-round").hide();
        $("#modal-dealer").hide();
        $("#reject-trump-button").show();
        $("#accept-trump-button").show();
        $(".suit-button").hide();
        $("#going-alone-checkbox").show();
        $("#going-alone-checkbox").prop("checked", false);
        $("#modal-trump .modal-content").html(`
            <img src="${getCardImage(card)}" class="playing-card" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%);" alt="Up Card">
        `);

        $("#reject-trump-button").prop("disabled", false);
    
        // Ensure buttons are properly assigned new handlers
        $("#accept-trump-button").off("click").on("click", function () {
            const goingAlone = $("#going-alone-checkbox").is(":checked");
            $("#modal-trump").fadeOut(); // Hide the modal before proceeding
            acceptTrump(player, card, 1, goingAlone);
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
        $("#modal-trick-play").hide();
        $("#ok-round-button").hide();
        $("#modal-round").fadeOut();
        $("#modal-dealer").fadeOut();
        $("#reject-trump-button").show();
        $("#accept-trump-button").hide();
        $(".suit-button").show();
        $("#going-alone-checkbox").show();
        $("#going-alone-checkbox").prop("checked", false);
        $("#modal-trump .modal-content").html(`
        `);

        // Enable all suit buttons
        $(".suit-button").prop("disabled", false);
        $("#reject-trump-button").prop("disabled", false);

        // Disable the button for the upcard suit
        $(`.suit-button[data-suit="${upCardSuit}"]`).prop("disabled", true);

        // Disable the pass button if player is the dealer
        if (player === gameResponse.dealer) {
            $("#reject-trump-button").prop("disabled", true);
        }

        $(".suit-button").off("click").on("click", function () {
            const selectedSuit = $(this).data("suit");
            const goingAlone = $("#going-alone-checkbox").is(":checked");
            $("#modal-trump").fadeOut(); // Hide the modal before proceeding
            acceptTrump(player, selectedSuit, 2, goingAlone);
        });

        $("#reject-trump-button").off("click").on("click", function () {
            $("#modal-trump").fadeOut();
            rejectTrump(player, 2);
        });

        $("#modal-trump").fadeIn(); // Ensure modal appears properly
    }
    
    // Store the human player's hand after trump is accepted
    function setPlayerHand(hand) {
        window.currentPlayerHand = hand.map(card => card.replace(" of ", "_of_").toLowerCase());
    }     

    function acceptTrump(player, card, trumpRound, goingAlone) {
        const data = {
            trump_round: String(trumpRound),
            player: String(player),
            going_alone: Boolean(goingAlone)
        };        
    
        if (trumpRound === 1 && card) {
            data.card = String(card);
        } else if (trumpRound === 2 && card) {
            data.suit = String(card);
        }
    
        console.log("📤 Sending trump data:", data);
    
        $.ajax({
            url: "/accept-trump/",
            type: "POST",
            data: JSON.stringify(data),
            contentType: "application/json",
            success: function (response) {
                console.log("🔥 Response received:", response);
                window.gameState.trumpSelected = true;
                currentSuit = response.trump_suit;
                dealer = response.dealer;
                discarded_card = response.discarded_card;
                updated_hand = response.updated_hand;

            
                kitty[0].faceup = false;
                if (response.discarded_card) {
                    kitty[0].card = response.discarded_card;
                }
                updateKittyDisplay();
    
                if (response.updated_hand) {
                    if (player === "Player") {
                        $("#human-card").empty(); // 🧹 Clear old cards from UI
                    }
                
                    window.currentPlayerHand = response.updated_hand.map(card =>
                        card.replace(" of ", "_of_").toLowerCase()
                    );
                
                    updatePlayerHand("Player", response.updated_hand); // 🖼️ Redraw hand
                    setPlayerHand(response.updated_hand); // 💾 Store hand in memory
                }                
            
                updateTrumpDisplay(currentSuit);
                updatePlayerNames(player, currentSuit);
    
                $("#modal-trump").fadeOut();
                const message = goingAlone
                    ? `${player} is <b>going alone</b> in ${currentSuit}.`
                    : `${player} called trump! The trump suit is now ${currentSuit}.`;
                showRoundStart(message, player, goingAlone);
    
                // 🟢 Start the round and trick loop
                startRound(player, goingAlone);
            },
            error: function (xhr) {
                console.error("❌ Error accepting trump:", xhr.responseText);
            }
        });
    }
    

    function updatePlayerNames(trumpCaller = null, trumpSuit = null) {
        $(".rectangle").removeClass("loner-partner");
        $("#modal-trick-play").hide();
        $(".center-top-text").text("Team Mate");
        $(".center-left-text").text("Opponent 1");
        $(".center-bottom-text").text("Player");
        $(".center-right-text").text("Opponent 2");

        // Add indicator to the player who called trump
        if (trumpCaller) {
            const nameMap = {
                "Player": ".center-bottom-text",
                "Opponent1": ".center-left-text",
                "Team Mate": ".center-top-text",
                "Opponent2": ".center-right-text"
            }

            const suitImageMap = {
                "spades": "/static/images/spade.png",
                "hearts": "/static/images/heart.png",
                "diamonds": "/static/images/diamond.png",
                "clubs": "/static/images/club.png"
            }
            
            const selector = nameMap[trumpCaller];
            const baseText = $(selector).text();
            if (selector.includes("center-left-text") || selector.includes("center-right-text")) {
                $(selector).html(`${baseText} <img src="${suitImageMap[trumpSuit]}" alt="${trumpSuit}" class="trump-caller-indicator ${selector === ".center-right-text" ? "right-indicator" : "left-indicator"}">`);
            } else {
                $(selector).html(`${baseText} <img src="${suitImageMap[trumpSuit]}" alt="${trumpSuit}" class="trump-caller-indicator">`);
            }
        }
    }


    function updatePlayerHand(player, cards) {
        const cardContainer = $(positions[player]);
        cardContainer.empty(); // Clear old hand
    
        cards.forEach(card => {
            const isHuman = player === "Player";
            const formatted = card.toLowerCase().replace(/ /g, "_");
            const imgSrc = isHuman ? `/static/images/cards/${formatted}.png` : getCardImage("Hidden");
    
            const $cardImg = $("<img>")
                .attr("src", imgSrc)
                .attr("alt", card)
                .addClass("playing-card") // ✅ Ensure consistent styling
                .attr("data-card", formatted)
                .attr("data-player", player);
    
            if (isHuman) {
                $cardImg.attr("draggable", true);
    
                $cardImg.on("dragstart", function (e) {
                    e.originalEvent.dataTransfer.setData("card", formatted); // ✅ Match drop zone logic
                    e.originalEvent.dataTransfer.effectAllowed = "move";
                    console.log("Dragging card:", formatted);
                });
            }
    
            cardContainer.append($cardImg);
        });
    }    
    

    const cardElements = document.querySelectorAll('.card'); // Select all card elements
    cardElements.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
    });

    function handleDragStart(e) {
        e.dataTransfer.setData("text", e.target.id); // Make sure you are setting the data correctly
    }


    document.getElementById("play-card-button").addEventListener("click", function () {
        const selectedCard = getSelectedCardFromModal();
        if (!selectedCard) return;
    
        gameState.awaitingCard = false;  // Allow polling again
        $("#modal-trick-play").hide();
    
        $.ajax({
            url: "/play-trick-step/",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ card: selectedCard }),
            success: function (response) {
                console.log("✅ Card played response:", response);
                playTrickLoop();  // Continue trick logic
            },
            error: function (err) {
                console.error("❌ Error playing card:", err);
            }
        });
    });

    function getCardImageFilename(card) {
        if (card.includes("_of_")) return `${card}.png`;
        const [rank, suit] = card.split(" of ");
        return `${rank.toLowerCase()}_of_${suit.toLowerCase()}.png`;
    }
    

    dropZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZone.style.borderColor = "#4CAF50";
    });

    dropZone.addEventListener("dragleave", function (e) {
        e.preventDefault();
        dropZone.style.borderColor = "#ccc";
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.innerHTML = ""; // Clear previous
    
        const card = e.dataTransfer.getData("card");
        if (!card || (!card.includes(" of ") && !card.includes("_of_"))) {
            console.error("❌ Invalid card format dropped:", card);
            return;
        }
    
        const cardFilename = getCardImageFilename(card);
        const img = document.createElement("img");
        img.src = `/static/images/cards/${cardFilename}`;
        img.classList.add("card", "card-in-modal");
    
        // Safely parse rank and suit
        let rank, suit;
    
        if (card.includes("_of_")) {
            [rank, suit] = card.split("_of_");
        } else if (card.includes(" of ")) {
            [rank, suit] = card.split(" of ");
        } else {
            console.error("❌ Could not split card into rank and suit:", card);
            return;
        }
    
        img.setAttribute("data-rank", rank.trim());
        img.setAttribute("data-suit", suit.trim());
    
        const formattedCard = `${rank.toUpperCase()} of ${capitalize(suit)}`;
        dropZone.appendChild(img);
    
        // Save the card being played
        dropZone.setAttribute("data-played-card", formattedCard); // Use consistent format
        playBtn.disabled = false;
    });
    
    
    
    if (dropZone.querySelector("img")) {
        console.log("Card already dropped.");
        return;
    }


    $("#start-round-button").on("click", function () {
        $.post("/start-next-round/", {}, function (res) {
            console.log("🔄 Starting next round...", res);
            startNextRound();  // <- this should make the AJAX POST to /start-round/
            $("#round-results-modal").fadeOut();
            resetTrickTable();
            resetCenter();
            $.post("/start-next-round/", function (res) {
                console.log("🔄 Starting new round...");
                $("#modal-round").hide();
                setTimeout(() => {
                    pollNextTrickStep();  // ✅ resume loop
                }, 600);
            });
        });
    // ❌ missing this ↓↓↓
    });    


    $("#modal-round-button").on("click", function () {
        $.post("/start-round/", {}, function (data) {
            console.log("▶️ New round started:", data);
            $("#modal-round").fadeOut();
            resetTrickTable();
            resetCenter();
            pollNextTrickStep();
        });
    });    
    

    $("#play-card-button").off("click").on("click", function () {
        const selectedCard = $("#drop-zone").attr("data-played-card");
        if (!selectedCard) return;
    
        $("#modal-trick-play").fadeOut();
        console.log("🃏 Playing card:", selectedCard);
        playCard(selectedCard);
    });    

    
    function rejectTrump(player, trumpRound) {
        currentPlayerIndex++;
    
        if (currentPlayerIndex < playerOrder.length) {
            if (trumpRound === 1) {
                setTimeout(() => {
                    if (playerOrder[currentPlayerIndex].is_human == true) {
                        showTrumpCardDialog(gameResponse.remaining_cards[0], playerOrder[currentPlayerIndex].name);
                    } else {
                        determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], trumpRound, playerOrder);
                    }
                }, 400); // Delay prevents modal flickering
            } else if (trumpRound === 2) {
                setTimeout(() => {
                    if (playerOrder[currentPlayerIndex].is_human == true) {
                        showTrumpCardDialog2ndRound(gameResponse.remaining_cards[0].split(" of ")[1], playerOrder[currentPlayerIndex].name);
                    } else {
                        determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], trumpRound, playerOrder);
                    }
                }, 400); // Delay prevents modal flickering
            }
        } else {
            // Everyone passed in first round, so start second round
            trumpRound = 2;
            currentPlayerIndex = 0;

            // Update kitty
            kitty[0].faceup = false;
            
            updateKittyDisplay();
            
            // Give trump dialog box, but this time player can select any suit except for the upCardSuit
            setTimeout(() => {
                if (playerOrder[currentPlayerIndex].is_human == true) {
                    showTrumpCardDialog2ndRound(gameResponse.remaining_cards[0].split(" of ")[1], playerOrder[currentPlayerIndex].name);
                } else {
                    determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], trumpRound, playerOrder);
                }
            }, 400);
        }
    }

    function determineBotTrumpDecision(player, upCard, trumpRound, playerOrder) {
        $.ajax({
            url: "/determine-trump/",
            type: "POST",
            data: {
                player: player,
                dealer: dealer,
                up_card: upCard,
                trump_round: trumpRound,
                player_order: JSON.stringify(playerOrder)
            },
            async: false,
            success: function (response) {
                const botDecision = response.decision;
                const goingAlone = response.going_alone;
                console.log("Bot decision:", botDecision);

                if (trumpRound === 1) {
                    if (botDecision === 'pass') {
                        $("#bot-messages").text(`${player} passes`).fadeIn().delay(400).fadeOut();
                        setTimeout(() => {
                            rejectTrump(player, trumpRound);
                        }, 800);
                    } else {
                        acceptTrump(player, upCard, trumpRound, goingAlone);
                    }
                } else if (trumpRound === 2) {
                    if (botDecision === 'pass') {
                        $("#bot-messages").text(`${player} passes`).fadeIn().delay(400).fadeOut();
                        setTimeout(() => {
                            rejectTrump(player, trumpRound);
                        }, 800);
                    } else {
                        acceptTrump(player, botDecision, trumpRound, goingAlone);
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
        $("#modal-trick-play").hide();
        $("#ok-modal-button").hide();
        $("#modal-round-button").hide();
        $("#ok-trump-button").show();  // Ensure OK button is visible
    
        $("#modal-trump").fadeIn(); // Ensure modal is visible
    }

    // Function to display the round status
    function showRoundStart(message, trumpCaller, goingAlone) {
        if (!trumpSelected) return;  // Prevents round modal from appearing too early

        $("#modal-trump").fadeOut(); // Hide trump modal if still visible
        $("#modal-trick-play").hide();
        $("#modal-round .modal-content").html(`
            <p>${message}</p>
        `);
    
        $("#modal-round-button").show();
        $("#modal-round").fadeIn();

        // Hide unnecessary buttons
        $("#accept-trump-button").hide();
        $("#reject-trump-button").hide();
        $("#ok-modal-button").hide();
        $("#ok-round-button").hide();
        $("#ok-trump-button").hide();
        $("#modal-round-button").show();

        if (goingAlone) {
            updateHandForLoner(trumpCaller, goingAlone);
        }

        $("#modal-round-button").off("click").on("click", function () {
            $("#modal-round").fadeOut();
            startRound(trumpCaller, goingAlone);
        });

        $("#modal-round").fadeIn(); // Ensure round modal is displayed
    }

    function updateHandForLoner(trumpCaller, goingAlone) {
        const partnerMap = {
            "Player": "Team Mate",
            "Opponent1": "Opponent2",
            "Opponent2": "Opponent1",
            "Team Mate": "Player"
        };

        const partner = partnerMap[trumpCaller];
        $(positions[partner]).addClass("loner-partner");
    }
    

    // Start the game
    $("#start-game-button").click(function () {

        // Hide the start game button
        $("#start-game-button").hide();
        $("#start-game-form").hide();

        $.ajax({
            url: "/start-game/", // Matches the URL in urls.py
            type: "POST",
            success: function (response) {
                console.log("New dealer is:", response.dealer); // Debugging log
            
                // ✅ Ensure dealer is highlighted and icon is added on first round
                $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();
            
                if (response.dealer && positions[response.dealer]) {
                    const dealerPosition = positions[response.dealer];
                
                    console.log(`✅ Updating dealer to: ${response.dealer}`);
                
                    $(dealerPosition).addClass("dealer-highlight");
                
                    // ✅ Only add the dealer icon if it's missing
                    if ($(dealerPosition).find(".dealer-icon").length === 0) {
                        $(dealerPosition).prepend(`
                            <img src="/static/images/dealer-icon.png" alt="Dealer Icon" class="dealer-icon">
                        `);
                    }
                }
                 else {
                    console.error("❌ Error: Dealer position not found in UI during game start.");
                }
            
                initializeDealerModal(response);
                displayHighCards(response); // Ensure high cards are shown
                playerOrder = response.player_order; // Set player order for trump selection
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
                playerOrder = response.player_order;
                currentPlayerIndex = 0;

                updateTrumpDisplay(null);
    
                initializeKitty(response.remaining_cards);
                displayDealtCards(response);
    
                // ✅ Ensure the dealer highlight and icon remain
                $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();
    
                if (dealer in positions) {
                    const dealerPosition = positions[dealer];
                    $(dealerPosition).addClass("dealer-highlight");
                    if ($(dealerPosition).find(".dealer-icon").length === 0) {
                        $(dealerPosition).prepend(`
                            <img src="/static/images/dealer-icon.png" alt="Dealer Icon" class="dealer-icon">
                        `);
                    }
                }

                // Start the trump card selection process
                if (playerOrder[currentPlayerIndex].is_human == true) {
                    showTrumpCardDialog(response.remaining_cards[0], playerOrder[currentPlayerIndex].name);
                } else {
                    determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], 1, playerOrder);
                }
            },
            error: function (xhr) {
                alert("An error occurred while dealing the hand: " + xhr.responseText);
            }
        });
    });    

    function initializeKitty(remainingCards) {
        console.log("Initializing kitty with:", remainingCards);
        kitty = remainingCards.map((card, index) => {
            return {
                card: card,
                faceup: index === 0
            }
        });
        updateKittyDisplay();
    }

    function updateKittyDisplay() {
        const kittyContainer = document.getElementById("kitty-container");
        if (!kittyContainer) return;
    
        kittyContainer.innerHTML = "";
    
        kitty.forEach(card => {
            const cardImg = document.createElement("img");
            cardImg.classList.add("playing-card");
    
            if (card.faceup && card.rank && card.suit) {
                const cardStr = `${card.rank} of ${card.suit}`;
                cardImg.src = getCardImage(`${card.rank}_of_${card.suit}`);
                cardImg.setAttribute("data-card", formatCardForDOM(cardStr));  // ✅ For DOM tracking
            } else {
                cardImg.src = getCardImage("Hidden");
                cardImg.setAttribute("data-card", "hidden");
            }
    
            kittyContainer.appendChild(cardImg);
        });
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
                determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], 1, playerOrder);
            }
        } else {
            showFinalMessage("No one accepted the trump card.");
            trumpSelected = false;
        }
    });

    function updateTrumpDisplay(suit) {
        const tooltipIconHTML = `
            <div class="tooltip-label">
                <strong>Current Trump</strong>
                <img src="/static/images/tooltip.png"
                    alt="Tooltip"
                    class="tooltip-icon"
                    data-tooltip-id="trump">
            </div>`;
    
        if (!suit) {
            $(".bottom-left-column-1").html(`
                ${tooltipIconHTML}
                <div class="icon-wrapper">
                    <img src="/static/images/card_suits.png" alt="Select Trump" class="trump-suit-icon">
                </div>
            `);
        } else {
            const suitImageMap = {
                "spades": "/static/images/spade.png",
                "hearts": "/static/images/heart.png",
                "diamonds": "/static/images/diamond.png",
                "clubs": "/static/images/club.png"
            };
            const suitImagePath = suitImageMap[suit];
    
            $(".bottom-left-column-1").html(`
                ${tooltipIconHTML}
                <div class="icon-wrapper">
                    <img src="${suitImagePath}" alt="${suit}" class="trump-suit-icon">
                </div>
            `);
        }
    
        // 🔁 Bind click behavior
        $(".tooltip-icon").off("click").on("click", function () {
            const tooltipId = $(this).data("tooltip-id");
            const message = tooltips[tooltipId] || "Tooltip not found.";
            $("#tooltip-content").html(message);
            $("#tooltip-modal").modal("show");
        });
    
        // 👀 Show or hide based on tooltipsEnabled
        if (window.tooltipsEnabled === false) {
            $(".tooltip-icon").hide();
        } else {
            $(".tooltip-icon").show();
        }
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


    // Function to show the round results modal
    function showRoundResults(results) {
        let winningMessage = results.winning_team
            ? `<p><strong>${results.winning_team} won the game!</strong></p>`
            : ``;

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

    function resetTrickTable() {
        $("#player-teammate-tricks").empty();
        $("#opponent-tricks").empty();
    }
    
    // Handle starting the round
    function startRound(trumpCaller, goingAlone) {
        console.log(`🔄 Starting round. Trump caller: ${trumpCaller}`);
    
        $.ajax({
            url: "/start-round/",
            type: "POST",
            data: { trump_caller: trumpCaller, going_alone: goingAlone },
            success: function (response) {
                console.log("✅ Round Results Received:", response);
                console.log("🔁 Human's hand ready:", window.currentPlayerHand);
                console.log("🃏 Awaiting human card click...");
    
                if (response.error) {
                    alert("❌ Error: " + response.error);
                    return;
                }
    
                if (response.tricks) {
                    updatePreviousTricks([response.tricks]); 
                }
    
                if (response.round_results) {
                    finalizeRound(response);
                }
    
                updateRemainingCards();
                revealKitty();
                resetTrickTable();
    
                window.gameState.trumpSelected = true;
                window.gameState.roundStarted = true;
                playTrickLoop();  // Then start the loop
            },
            error: function (xhr) {
                alert("❌ Error starting round: " + xhr.responseText);
            }
        });
    }
    

    function revealKitty() {
        kitty.forEach(item => item.faceup = true);
        updateKittyDisplay();
    }
    
    
    // OK button to close round results modal, and start next round trump selection
    $("#ok-round-button").click(function () {
        $("#modal-round").fadeOut();  // Hide the round results modal
        // dealNextHand(); // ✅ Fix: Ensure trump selection happens first
        // Reset player names to remove trump indicator
        updatePlayerNames();
    
        $.ajax({
            url: "/deal-next-hand/",  // Redeal hands and rotate dealer
            type: "POST",
            success: function (response) {

                gameResponse = response;
                playerOrder = response.player_order;
                currentPlayerIndex = 0;

                updateTrumpDisplay(null);
                
                initializeKitty(response.remaining_cards);
                displayDealtCards(response);
                updateDealerPosition(response);

                // ✅ Show the trump card selection dialog with the first remaining card
                $("#modal-round").fadeOut();
                setTimeout(() => {
                    if (playerOrder[currentPlayerIndex].is_human == true) {
                        showTrumpCardDialog(response.remaining_cards[0], playerOrder[currentPlayerIndex].name);
                    } else {
                        determineBotTrumpDecision(playerOrder[currentPlayerIndex].name, gameResponse.remaining_cards[0], 1, playerOrder);
                    }
                }, 300);  // Adds delay to ensure previous modal fully closes
            }
        }).fail(function(error) {
                console.error("🚨 Error dealing next hand: ", error);
        });
    });


    function pollNextTrickStep() {
        // 💥 Prevent polling if round is already over
        if (window.roundOver) {
            console.warn("🛑 Round already completed. Skipping trick step polling.");
            return;
        }

        // 👤 Human player's turn
        if (gameState.awaitingCard) {
            const selected = getSelectedCardFromModal();
    
            if (!selected) {
                console.warn("⚠️ No card selected in modal yet. Waiting...");
                return;
            }
    
            console.log("📤 Sending selected card:", selected);
    
            $.ajax({
                type: "POST",
                url: "/play-trick-step/",
                data: JSON.stringify({ card: selected }),
                contentType: "application/json",
                success: function (data) {
                    gameState.awaitingCard = false;
    
                    if (data.trick_complete) {
                        updatePreviousTrick(data.trick);
    
                        if (data.action === "round_completed" && data.round_results) {
                            finalizeRound(data);
                            window.roundOver = true;  // ✅ Prevent further polling
                            return;
                        }
    
                        setTimeout(() => pollNextTrickStep(), 1000);
                    } else {
                        setTimeout(() => pollNextTrickStep(), 500);
                    }
                },
                error: function (err) {
                    console.error("❌ Failed to play card:", err.responseJSON);
                }
            });
    
            return;
        }
    
        // 🤖 Bot or server updates
        $.get('/play-trick-step/', function (data) {
            if (data.action === 'awaiting_player') {
                gameState.awaitingCard = true;
                console.log("🃏 Awaiting human card selection...");
                showTrickModal(data);
            } else if (data.action === 'bot_played') {
                console.log("🤖 Bot played card:", data.card);
                removeCardFromPlayerHand(formatCardForDOM(data.card), data.player);
                setTimeout(() => pollNextTrickStep(), 500);
            } else if (data.action === 'trick_completed') {
                updatePreviousTrick(data.trick);
    
                if (data.action === "round_completed" && data.round_results) {
                    finalizeRound(data);
                    window.roundOver = true;  // ✅ Prevent further polling
                    return;
                }
    
                setTimeout(() => pollNextTrickStep(), 1000);
            }
        }).fail(function (err) {
            console.error("❌ Failed to fetch trick step:", err.responseText);
        });
    }

    function showNextRoundDialog(roundResults) {
        console.log("📢 Showing round dialog with results:", roundResults);
    
        window.gameState.awaitingCard = false;
        $("#modal-trick-play").hide();
        $("#modal-trump").hide();
        $(".custom-modal").not("#round-results-modal").fadeOut();  // hide all but round modal
        $("#round-results-modal .modal-actions button").hide();     // hide all modal buttons
    
        if (roundResults.game_over) {
            $("#end-game-button").show();
        } else {
            $("#start-round-button").show();  // ✅ Correct button
        }
    
        $("#play-card-modal").hide();
    
        $("#round-results-content").html(`
            <h2>Round Complete</h2>
            <p>Winning Team: ${roundResults.winning_team}</p>
            <p>Points Earned: ${roundResults.points_earned || 1}</p>
            <p>Total Scores: Team 1 - ${roundResults.team1_score}, Team 2 - ${roundResults.team2_score}</p>
        `);
    
        $("#round-results-modal").fadeIn();
    }    
    
    
    function getSelectedCardFromModal() {
        const cardImg = dropZone.querySelector("img");
    
        if (!cardImg) return null;
    
        const rank = cardImg.dataset.rank;
        const suit = cardImg.dataset.suit;
    
        if (!rank || !suit) return null;
    
        return `${rank} of ${suit}`;
    }      
    

    function resetCenter() {
        // Reset the center area by clearing out any played cards
        ["team-mate", "opponent1", "opponent2", "player"].forEach(id => {
            $(`#trick-${id}`).empty();
        });

        // Optionally, reset any visual effects on the drop zone
        $("#drop-zone").removeClass("card-played");  // Remove any played card styles
    }
    
    function playCard(cardId) {
        if (!gameState.awaitingCard) {
            console.warn("⛔ It's not your turn yet. Card play blocked.");
            return;
        }
    
        const humanCard = formatCard(cardId);
        console.log("🃏 Playing card:", humanCard);
        gameState.awaitingCard = false;
    
        $("#play-card-button").prop("disabled", true);
    
        if (typeof humanCard !== "string" || !humanCard.includes(" of ")) {
            console.error("❌ Invalid card format:", humanCard);
            return;
        }
    
        $.ajax({
            url: "/play-trick-step/",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ card: humanCard }),
            success: function (response) {
                console.log("✅ Card played:", response);
                const trick = response.trick;
    
                // Remove from UI and hand
                const playerIndex = trick.players.indexOf("Player");
                if (playerIndex !== -1) {
                    const playedCard = trick.cards[playerIndex];
                    const domId = formatCardForDOM(playedCard);
                    removeCardFromPlayerHand(domId, "Player");
                    window.currentPlayerHand = window.currentPlayerHand.filter(c => c !== domId);
                    updatePlayerHand("Player", window.currentPlayerHand.map(c => c.replace("_of_", " of ")));
                    console.log(`📤 Player played: ${playedCard}`);
                }
    
                updatePreviousTricksTable(trick);
    
                // Hide modal and clear zone
                $("#drop-zone").empty().removeAttr("data-played-card");
                $("#play-card-modal").fadeOut();
    
                // Round complete handling
                if (response.trick_complete && response.trick) {
                    if (response.trick_complete && response.trick) {
                        if (response.action === "round_completed" && response.round_results) {
                            updatePreviousTricks([response.tricks]); 
                            
                            if (response.round_results.game_over) {
                                finalizeRound(response); // shows End Game modal
                                showRoundResultsModal(response.round_results); // optional legacy UI
                            } else {
                                showNextRoundDialog(response.round_results);  // 👈 Start Round button
                                updatePreviousTrick(response.trick);
                                finalizeRound(response);
                            }
                    
                            return;  // ✅ Exit to avoid extra polling
                        }
                    
                        // If the trick just ended and we're continuing
                        setTimeout(() => {
                            $("#drop-zone").empty().removeAttr("data-played-card");
                            $("#play-card-modal").hide();
                            $("#end-game-button").hide();
                            $("#ok-round-button").hide();
                            resetCenter();  // 👈 move this *after* modal hides
                            gameState.awaitingCard = false;
                            pollNextTrickStep();
                        }, 1200);
                    }                    
                }                  
            },
            error: function (xhr) {
                console.error("❌ Failed to play card:", xhr.responseText);
                $("#play-card-button").prop("disabled", false);
                alert("⚠️ Could not play the card: " + (xhr.responseJSON?.error || "Unknown error"));
            }
        });
    }    
    

    function updateDealerPosition(response) {
        console.log("New dealer is:", response.dealer); // Debugging log
    
        // ✅ Check if the dealer exists in the positions mapping
        console.log("✅ Available positions keys:", Object.keys(positions)); 
        console.log("✅ Received dealer:", response.dealer);
    
        const normalizedDealer = response.dealer.trim();  // Remove extra spaces

        if (!positions[normalizedDealer]) {
            console.error(`❌ Error: No position found for dealer "${normalizedDealer}"`);
            return;  // Exit early to prevent further errors
        }
        
        const dealerPosition = positions[normalizedDealer];
        
        console.log(`✅ Updating dealer to: ${normalizedDealer}`);
        console.log("✅ Dealer position element:", $(dealerPosition)); // Log the actual element
        
        const dealerName = response.dealer.trim();  // Ensure correct dealer name

        if (dealerName in positions) {
            const dealerPosition = positions[dealerName];
        
            // ✅ First, clear only if a valid dealer position exists
            $(".rectangle").removeClass("dealer-highlight").find(".dealer-icon").remove();
        
            $(dealerPosition).addClass("dealer-highlight");
            if ($(dealerPosition).find(".dealer-icon").length === 0) {
                $(dealerPosition).prepend(`
                    <img src="/static/images/dealer-icon.png" alt="Dealer Icon" class="dealer-icon">
                `);
            }
        } else {
            console.error(`❌ Error: No valid dealer position found for "${dealerName}"`);
        }
    }
    


    // End game when one team reaches the points to win
    $("#end-game-button").click(function () {
        $.ajax({
            url: "/reset-game/",  // Reset the game state
            type: "POST",
            success: function (response) {
                console.log(response.message);
                // Reset Current Trump and Game Score on Page Load
                $("#current-trump").text("None");
                $("#game-score").text("Player Team: 0 | Opponent Team: 0");
    
                // Close all modals and reset the UI
                $(".custom-modal").fadeOut();
                $("#remaining-cards-list").html("<p></p>");
                
                updatePlayerNames();

                // Show the Start Game button again
                $("#end-game-button").hide();
                $("#start-game-button").show();
                $("#modal-trick-play").hide();
                $("#start-game-form").show();
            },
            error: function (xhr) {
                alert("Error ending the game: " + xhr.responseText);
            }
        });
    });

    function updatePreviousTricksTable(trick) {
        if (!trick || !trick.trick_number) return;
    
        const existing = $("#trick-table-player tbody").find(`tr[data-trick="${trick.trick_number}"]`);
        if (existing.length > 0) {
            console.warn(`⚠️ Trick #${trick.trick_number} already logged, skipping.`);
            return;
        }
    
        const row = `<tr data-trick="${trick.trick_number}">
            <td>${trick.trick_number}</td>
            <td>${trick.players.join(", ")}</td>
            <td>${trick.cards.join(", ")}</td>
            <td>${trick.winner}</td>
        </tr>`;
        $("#trick-table-player tbody").append(row);
    }
    
    

    // Function to update game score
    function updateGameScore(team1, team2) {
        $(".bottom-left-column-2").html(`
            <div class="tooltip-label">
                <strong>Game Score</strong>
                <img src="/static/images/tooltip.png" 
                     alt="Tooltip" 
                     class="tooltip-icon" 
                     data-tooltip-id="score">
            </div>
            <p style="padding-top: 30px; font-size: large;">Player Team: ${team1} points</p>
            <p style="padding-top: 10px; font-size: large;">Opponent Team: ${team2} points</p>
        `);
    
        $(".tooltip-icon").off("click").on("click", function () {
            const tooltipId = $(this).data("tooltip-id");
            const message = tooltips[tooltipId] || "Tooltip not found.";
            $("#tooltip-content").html(message);
            $("#tooltip-modal").modal("show");
        });
    
        // 👀 Respect tooltip toggle state
        if (window.tooltipsEnabled === false) {
            $(".tooltip-icon").hide();
        } else {
            $(".tooltip-icon").show();
        }
    }    

    function updateRemainingCards(showCards=false) {
        const redSuits = ["hearts", "diamonds"]; // First row
        const blackSuits = ["clubs", "spades"]; // Second row
        const suits = [...redSuits, ...blackSuits]; // Full order
        const ranks = ["A", "K", "Q", "J", "10", "9"]; // Descending rank order
    
        // Generate the full deck of 24 cards
        let fullDeck = [];
        suits.forEach(suit => {
            ranks.forEach(rank => {
                fullDeck.push(`${rank} of ${suit}`);
            });
        });
    
        $.ajax({
            url: "/get-remaining-cards/",
            type: "GET",
            success: function (response) {
                if (response.remaining_cards) {
                    // Filter out used cards
                    const usedCards = response.remaining_cards;
                    let availableCards = fullDeck.filter(card => usedCards.includes(card));
    
                    // Sort the available cards: Grouped by suit, descending by rank
                    availableCards.sort((a, b) => {
                        let [rankA, suitA] = a.split(" of ");
                        let [rankB, suitB] = b.split(" of ");
    
                        let suitIndexA = suits.indexOf(suitA);
                        let suitIndexB = suits.indexOf(suitB);
    
                        if (suitIndexA !== suitIndexB) {
                            return suitIndexA - suitIndexB; // Sort by suit order
                        }
                        return ranks.indexOf(rankA) - ranks.indexOf(rankB); // Sort descending within suit
                    });
    
                    // Group cards into two rows
                    let redRowHTML = ""; // Hearts & Diamonds
                    let blackRowHTML = ""; // Clubs & Spades
    
                    availableCards.forEach(card => {
                        let suit = card.split(" of ")[1];
                        let cardHTML = `<img src="${getCardImage(card)}" class="playing-card" data-card="${formatCardForDOM(card)}">`;
                        
                        if (redSuits.includes(suit)) {
                            redRowHTML += cardHTML;
                        } else if (blackSuits.includes(suit)) {
                            blackRowHTML += cardHTML;
                        }
                    });
    
                    // Update the UI for remaining cards
                    $("#remaining-cards-list").html(`
                        <div class="card-row">${redRowHTML}</div>
                        <div class="card-row">${blackRowHTML}</div>
                    `);
                } else {
                    $("#remaining-cards-list").html("<p>Error loading remaining cards.</p>");
                }
            },
            error: function (xhr) {
                console.error("Error fetching remaining cards:", xhr.responseText);
                $("#remaining-cards-list").html("<p>Error loading remaining cards.</p>");
            }
        });
    }
    

    function updatePreviousTricks(tricks) {
        const playerTeammateBody = document.getElementById("player-teammate-tricks");
        const opponentBody = document.getElementById("opponent-tricks");
    
        // Clear previous data
        playerTeammateBody.innerHTML = "";
        opponentBody.innerHTML = "";

        if (!trick || !trick.players || !trick.cards || trick.players.length !== 4 || trick.cards.length !== 4 || !trick.winner) {
            console.warn("⚠️ Skipping incomplete trick update:", trick);
            return;
        }
    
        const existing = $(`#trick-table-player tbody tr[data-trick="${trick.trick_number}"]`);
        if (existing.length > 0) {
            console.warn(`⚠️ Trick #${trick.trick_number} already logged, skipping.`);
            return;
        }
    
        if (!Array.isArray(tricks)) {
            tricks = [tricks];
        }
    
        if (tricks.length === 0) {
            playerTeammateBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">No tricks played yet.</td></tr>`;
            opponentBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">No tricks played yet.</td></tr>`;
            return;
        }
    
        const formatCard = (card) => card ? card : "—";
    
        tricks.forEach((trick) => {
            const player = "Player";
            const opponent1 = "Opponent1";
            const teammate = "Team Mate";
            const opponent2 = "Opponent2";
    
            const playerIndex = trick.players.indexOf(player);
            const opponent1Index = trick.players.indexOf(opponent1);
            const teammateIndex = trick.players.indexOf(teammate);
            const opponent2Index = trick.players.indexOf(opponent2);
    
            const playerCard = playerIndex !== -1 ? trick.cards[playerIndex] : "—";
            const opponent1Card = opponent1Index !== -1 ? trick.cards[opponent1Index] : "—";
            const teammateCard = teammateIndex !== -1 ? trick.cards[teammateIndex] : "—";
            const opponent2Card = opponent2Index !== -1 ? trick.cards[opponent2Index] : "—";
    
            const winner = trick.winner || "Unknown";
    
            const playerTeamWinClass = (winner === player || winner === teammate) ? "winner-green" : "";
            const opponentTeamWinClass = (winner === opponent1 || winner === opponent2) ? "winner-red" : "";
    
            const playerRow = `
                <tr>
                    <td>${trick.trick_number}</td>
                    <td>${player}</td>
                    <td>${formatCard(playerCard)}</td>
                    <td>${teammate}</td>
                    <td>${formatCard(teammateCard)}</td>
                    <td class="${playerTeamWinClass}">${winner}</td>
                </tr>
            `;
            playerTeammateBody.innerHTML += playerRow;
    
            const opponentRow = `
                <tr>
                    <td>${trick.trick_number}</td>
                    <td>${opponent1}</td>
                    <td>${formatCard(opponent1Card)}</td>
                    <td>${opponent2}</td>
                    <td>${formatCard(opponent2Card)}</td>
                    <td class="${opponentTeamWinClass}">${winner}</td>
                </tr>
            `;
            opponentBody.innerHTML += opponentRow;
        });
    }
    
    
    function appendTrickToHistory(trick) {
        const existing = $("#trick-table-player tbody").find(`tr[data-trick="${trick.trick_number}"]`);
        if (existing.length > 0) {
            console.warn(`⚠️ Trick #${trick.trick_number} already logged, skipping.`);
            return;
        }
        const playerTeammateBody = document.getElementById("player-teammate-tricks");
        const opponentBody = document.getElementById("opponent-tricks");
    
        const player = "Player";
        const opponent1 = "Opponent1";
        const teammate = "Team Mate";
        const opponent2 = "Opponent2";
    
        const playerIndex = trick.players.indexOf(player);
        const opponent1Index = trick.players.indexOf(opponent1);
        const teammateIndex = trick.players.indexOf(teammate);
        const opponent2Index = trick.players.indexOf(opponent2);
    
        const formatCard = (card) => card ? card : "—";
    
        const playerCard = playerIndex !== -1 ? trick.cards[playerIndex] : "";
        const opponent1Card = opponent1Index !== -1 ? trick.cards[opponent1Index] : "";
        const teammateCard = teammateIndex !== -1 ? trick.cards[teammateIndex] : "";
        const opponent2Card = opponent2Index !== -1 ? trick.cards[opponent2Index] : "";
    
        const winner = trick.winner || "Unknown";
    
        const playerTeamWinClass = (winner === player || winner === teammate) ? "winner-green" : "";
        const opponentTeamWinClass = (winner === opponent1 || winner === opponent2) ? "winner-red" : "";
    
        const playerRow = `
            <tr>
                <td>${trick.trick_number}</td>
                <td>${player}</td>
                <td>${formatCard(playerCard)}</td>
                <td>${teammate}</td>
                <td>${formatCard(teammateCard)}</td>
                <td class="${playerTeamWinClass}">${winner}</td>
            </tr>
        `;
    
        const opponentRow = `
            <tr>
                <td>${trick.trick_number}</td>
                <td>${opponent1}</td>
                <td>${formatCard(opponent1Card)}</td>
                <td>${opponent2}</td>
                <td>${formatCard(opponent2Card)}</td>
                <td class="${opponentTeamWinClass}">${winner}</td>
            </tr>
        `;
    
        playerTeammateBody.innerHTML += playerRow;
        opponentBody.innerHTML += opponentRow;
    }
    
    
    function showNextRoundDialog(roundResults) {
        console.log("📢 Showing round dialog with results:", roundResults);
    
        window.gameState.awaitingCard = false;
        $("#modal-trick-play").hide();
        $("#modal-trump").hide();
        $(".custom-modal").not("#round-results-modal").fadeOut();  // hide all but round modal
        $("#round-results-modal .modal-actions button").hide();     // hide all modal buttons
    
        if (roundResults.game_over) {
            $("#end-game-button").show();
        } else {
            $("#start-round-button").show();  // ✅ Correct button
        }
    
        $("#play-card-modal").hide();
    
        $("#round-results-content").html(`
            <h2>Round Complete</h2>
            <p>Winning Team: ${roundResults.winning_team}</p>
            <p>Points Earned: ${roundResults.points_earned || 1}</p>
            <p>Total Scores: Team 1 - ${roundResults.team1_score}, Team 2 - ${roundResults.team2_score}</p>
        `);
    
        $("#round-results-modal").fadeIn();
    }
    
    
    

    function updatePreviousTrick(trick) {
        console.log("🧾 Updating Previous Trick Table:", trick);
        appendTrickToHistory(trick);
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