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
    /* Render any new radar charts in swapped content */
    renderRadarCharts(e.detail.target);
});

/* ══════════════════════════════════════════════════════════
   Radar Chart — 11-axis resonance visualization
   Pure SVG, no dependencies
   ══════════════════════════════════════════════════════════ */

var RADAR_AXES = [
    { key: "exploration_execution", label: "EXPL" },
    { key: "alignment_tension",    label: "ALGN" },
    { key: "depth_breadth",        label: "DPTH" },
    { key: "momentum_resistance",  label: "MMTM" },
    { key: "novelty_familiarity",  label: "NOVL" },
    { key: "confidence_uncertainty", label: "CONF" },
    { key: "autonomy_direction",   label: "AUTO" },
    { key: "energy_entropy",       label: "ENRG" },
    { key: "vulnerability_performance", label: "VULN" },
    { key: "stakes_casual",        label: "STKS" },
    { key: "mutual_transactional", label: "MTUL" }
];

var AXIS_NAMES = {
    exploration_execution: "Exploration / Execution",
    alignment_tension: "Alignment / Tension",
    depth_breadth: "Depth / Breadth",
    momentum_resistance: "Momentum / Resistance",
    novelty_familiarity: "Novelty / Familiarity",
    confidence_uncertainty: "Confidence / Uncertainty",
    autonomy_direction: "Autonomy / Direction",
    energy_entropy: "Energy / Entropy",
    vulnerability_performance: "Vulnerability / Performance",
    stakes_casual: "Stakes / Casual",
    mutual_transactional: "Mutual / Transactional"
};

function polarToCartesian(cx, cy, radius, angleDeg) {
    var rad = (angleDeg - 90) * Math.PI / 180;
    return {
        x: cx + radius * Math.cos(rad),
        y: cy + radius * Math.sin(rad)
    };
}

function createSVGElement(tag, attrs) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in attrs) {
        el.setAttribute(k, attrs[k]);
    }
    return el;
}

function renderRadarChart(container) {
    var dataStr = container.getAttribute("data-resonance");
    var size = parseInt(container.getAttribute("data-size") || "180", 10);
    var data;
    try {
        data = JSON.parse(dataStr);
    } catch (e) {
        return;
    }

    var cx = size / 2;
    var cy = size / 2;
    var maxR = size * 0.38;
    var labelR = size * 0.47;
    var n = RADAR_AXES.length;
    var angleStep = 360 / n;

    var svg = createSVGElement("svg", {
        width: size,
        height: size,
        viewBox: "0 0 " + size + " " + size
    });

    /* Guide rings at 25%, 50% (zero line), 75%, 100% */
    var rings = [0.25, 0.5, 0.75, 1.0];
    rings.forEach(function (frac) {
        var cls = frac === 0.5 ? "radar-guide-ring zero-ring" : "radar-guide-ring";
        /* Draw guide ring as polygon for consistent shape */
        var pts = [];
        for (var i = 0; i < n; i++) {
            var p = polarToCartesian(cx, cy, maxR * frac, i * angleStep);
            pts.push(p.x.toFixed(1) + "," + p.y.toFixed(1));
        }
        var poly = createSVGElement("polygon", {
            points: pts.join(" "),
            "class": cls
        });
        svg.appendChild(poly);
    });

    /* Axis lines from center to outer edge */
    for (var i = 0; i < n; i++) {
        var outer = polarToCartesian(cx, cy, maxR, i * angleStep);
        var line = createSVGElement("line", {
            x1: cx, y1: cy,
            x2: outer.x, y2: outer.y,
            "class": "radar-axis-line"
        });
        svg.appendChild(line);
    }

    /* Data polygon */
    var hasData = Object.keys(data).length > 0;
    var points = [];
    var vertices = [];

    for (var i = 0; i < n; i++) {
        var axis = RADAR_AXES[i];
        var val = hasData ? (data[axis.key] || 0) : 0;
        /* Map -1..1 to 0..1 for radius fraction */
        var frac = (val + 1) / 2;
        var p = polarToCartesian(cx, cy, maxR * frac, i * angleStep);
        points.push(p.x.toFixed(1) + "," + p.y.toFixed(1));
        vertices.push({ x: p.x, y: p.y, axis: axis, val: val });
    }

    if (hasData) {
        var polygon = createSVGElement("polygon", {
            points: points.join(" "),
            "class": "radar-polygon animate"
        });
        svg.appendChild(polygon);

        /* Vertex dots */
        vertices.forEach(function (v) {
            var dot = createSVGElement("circle", {
                cx: v.x, cy: v.y,
                "class": "radar-vertex",
                "data-axis": v.axis.key,
                "data-value": v.val.toFixed(2)
            });
            svg.appendChild(dot);
        });
    }

    /* Axis labels */
    for (var i = 0; i < n; i++) {
        var lp = polarToCartesian(cx, cy, labelR, i * angleStep);
        var text = createSVGElement("text", {
            x: lp.x, y: lp.y,
            "class": "radar-label"
        });
        text.textContent = RADAR_AXES[i].label;
        svg.appendChild(text);
    }

    container.innerHTML = "";
    container.appendChild(svg);

    /* Tooltip on hover */
    if (hasData) {
        var tooltip = document.createElement("div");
        tooltip.className = "radar-tooltip";
        container.style.position = "relative";
        container.appendChild(tooltip);

        svg.addEventListener("mouseover", function (e) {
            if (e.target.classList.contains("radar-vertex")) {
                var axisKey = e.target.getAttribute("data-axis");
                var value = e.target.getAttribute("data-value");
                tooltip.textContent = (AXIS_NAMES[axisKey] || axisKey) + ": " + value;
                tooltip.classList.add("visible");
                var cx = parseFloat(e.target.getAttribute("cx"));
                var cy = parseFloat(e.target.getAttribute("cy"));
                tooltip.style.left = cx + "px";
                tooltip.style.top = (cy - 30) + "px";
            }
        });

        svg.addEventListener("mouseout", function (e) {
            if (e.target.classList.contains("radar-vertex")) {
                tooltip.classList.remove("visible");
            }
        });
    }
}

function renderRadarCharts(root) {
    var containers = (root || document).querySelectorAll(".radar-container");
    containers.forEach(function (c) {
        if (!c.querySelector("svg")) {
            renderRadarChart(c);
        }
    });
}

/* Render all radar charts on page load */
document.addEventListener("DOMContentLoaded", function () {
    renderRadarCharts();
});
