
let trickInProgress = false;
let currentPlayerName = "Player";  // Make dynamic if needed

function renderPlayerHand(playedSoFar, playerHand) {
    $("#human-card").empty();

    playerHand.forEach(card => {
        const normalized = card.replace(/ /g, "_");
        const cardDiv = $(`<img class="card" src="/static/images/cards/${normalized}.png" alt="${card}">`);        
        cardDiv.on("click", () => playCardAsHuman(card));
        $("#human-card").append(cardDiv);
    });

    // Optional: Show what others have played in this trick
    $("#bot-messages").html(
        playedSoFar.map(entry => `${entry.player} played ${entry.card}`).join("<br>")
    ).fadeIn().delay(2000).fadeOut();
}


function playCardAsHuman(cardStr) {
    fetch('/play-trick-step/', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card: cardStr })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
            return;
        }

        if (data.action === "trick_completed") {
            showTrickResults(data);
        } else if (data.action === "round_completed") {
            showTrickResults(data);  // Optional: handle round-end here
        }
    })
    .catch(error => {
        console.error("Error playing card:", error);
    });
}



function showTrickResults(data) {
    const trickHtml = data.cards_played.map(pc =>
        `<li>${pc.player} played ${pc.card}</li>`).join("");

    $("#modal-trick-play").html(`
        <p><strong>Trick Complete!</strong></p>
        <ul>${trickHtml}</ul>
        <p><strong>Winner: ${data.winner}</strong></p>
    `);
    $("#modal-round-button").hide();
    $("#ok-round-button").show();
    $("#modal-trick-play").fadeIn();

    $("#ok-round-button").off("click").on("click", () => {
        $("#modal-trick-play").fadeOut();

        // 💡 Clear last trick from backend, then restart trick loop
        $.post('/end-trick/', {}, function() {
            setTimeout(playTrickLoop, 500);
        });
    });
}
