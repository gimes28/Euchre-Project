// toggle tooltips, window makes it a global variable, accessible from other files
window.tooltipsEnabled = true;

$("#toggle-tooltips").on("click", function () {
    tooltipsEnabled = !tooltipsEnabled;

    if (tooltipsEnabled) {
        $(".tooltip-icon").show();
        $(this).text("Hide Euchre Tips");
    } else {
        $(".tooltip-icon").hide();
        $(this).text("Show Euchre Tips");
    }
});

$(document).ready(function () {
    $(".ui.dropdown").dropdown();

    // Set correct initial text
    $("#toggle-tooltips").text(tooltipsEnabled ? "Hide Euchre Tips" : "Show Euchre Tips");
});


// tooltip helper to display tooltip modals
$(document).ready(function () {
    $(".tooltip-icon").on("click", function () {
        const tooltipId = $(this).data("tooltip-id");
        const message = tooltips[tooltipId] || "Tooltip not found.";
        $("#tooltip-content").html(message);  // ✅ use .html instead of .text
        $("#tooltip-modal").modal("show");
    });
});