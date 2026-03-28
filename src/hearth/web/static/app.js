/* Hearth Web UI — minimal JavaScript */

/* Focus search box on "/" key */
document.addEventListener("keydown", function (e) {
    if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        var search = document.querySelector(".search-input");
        if (search) search.focus();
    }
});

/* Close modals/details on Escape */
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
        var openDetail = document.querySelector(".detail-expanded");
        if (openDetail) openDetail.remove();
    }
});
