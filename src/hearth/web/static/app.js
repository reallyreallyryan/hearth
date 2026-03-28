/* ══════════════════════════════════════════════════════════
   Hearth — UI Interactions
   ══════════════════════════════════════════════════════════ */

/* Focus search box on "/" key */
document.addEventListener("keydown", function (e) {
    if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        var search = document.querySelector(".search-input");
        if (search) {
            search.focus();
            search.select();
        }
    }
});

/* Close modals/details on Escape */
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
        var focused = document.activeElement;
        if (focused && focused.classList.contains("search-input")) {
            focused.blur();
            focused.value = "";
            /* Trigger htmx to reload the list */
            htmx.trigger(focused, "search");
        }
    }
});

/* Re-animate rows after htmx swap */
document.addEventListener("htmx:afterSwap", function (e) {
    var rows = e.detail.target.querySelectorAll("tbody tr");
    rows.forEach(function (row, i) {
        row.style.animationDelay = (i * 0.03) + "s";
    });
});
