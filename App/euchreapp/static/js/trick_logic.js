
let trickInProgress = false;
let currentPlayerHand = [];  // Store human's cards
let currentPlayerName = "Player";  // Make dynamic if needed


function renderPlayerHand(playedSoFar) {
    $("#human-card").empty();

    currentPlayerHand.forEach(card => {
        const normalized = card.replace(/ /g, "_");
        const cardDiv = $(`<img class="playing-card" src="/static/images/cards/${normalized}.png" alt="${card}">`);        
        cardDiv.on("click", () => playCardAsHuman(card));
        $("#human-card").append(cardDiv);
    });

    // Optional: Show what others have played in this trick
    $("#bot-messages").html(
        playedSoFar.map(entry => `${entry.player} played ${entry.card}`).join("<br>")
    ).fadeIn().delay(2000).fadeOut();
}


function playCardAsHuman(cardStr) {
    fetch('/play-card/', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card: cardStr, player: currentPlayerName })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert("Error: " + data.error);
                return;
            }

            if (data.action === "trick_completed") {
                showTrickResults(data);
            }
        })
        .catch(error => {
            console.error("Error playing card:", error);
        });
}


function showTrickResults(data) {
    const trickHtml = data.cards_played.map(pc =>
        `<li>${pc.player} played ${pc.card}</li>`).join("");

    $("#modal-round .modal-content").html(`
        <p><strong>Trick Complete!</strong></p>
        <ul>${trickHtml}</ul>
        <p><strong>Winner: ${data.winner}</strong></p>
    `);
    $("#modal-round-button").hide();
    $("#ok-round-button").show();
    $("#modal-round").modal("show");

    $("#ok-round-button").off("click").on("click", () => {
        $("#modal-round").modal("hide");

        // 💡 Clear last trick from backend, then restart trick loop
        $.post('/end-trick/', {}, function() {
            setTimeout(playTrickLoop, 500);
        });
    });
}
