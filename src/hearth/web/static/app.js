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

/* Render all visualizations on page load.
   app.js loads at the end of <body>, so the DOM may already be ready. */
function initVisualizations() {
    renderRadarCharts();
    /* Render drift heatmap if present */
    if (document.getElementById("heatmap-canvas") && typeof DRIFT_DATA !== "undefined") {
        renderDriftHeatmap("heatmap-canvas", DRIFT_DATA, DRIFT_INFLECTIONS || []);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initVisualizations);
} else {
    initVisualizations();
}


/* ══════════════════════════════════════════════════════════
   Drift — Heatmap + Sparkline Visualization
   Canvas-based, no dependencies
   ══════════════════════════════════════════════════════════ */

var currentDriftAxis = null;

function driftColor(value) {
    /* Map -1.0..1.0 to warm amber (positive) or cool blue (negative). */
    var abs = Math.abs(value);
    var r, g, b;

    if (value >= 0) {
        if (abs >= 0.7)      { r = 232; g = 145; b = 58; }   /* #e8913a ember */
        else if (abs >= 0.3) { r = 186; g = 120; b = 48; }   /* #ba7830 */
        else                 { r = 58;  g = 48;  b = 32; }   /* #3a3020 */
    } else {
        if (abs >= 0.7)      { r = 107; g = 138; b = 173; }  /* #6b8aad info blue */
        else if (abs >= 0.3) { r = 42;  g = 74;  b = 106; }  /* #2a4a6a */
        else                 { r = 32;  g = 42;  b = 48; }   /* #202a30 */
    }

    /* Interpolate intensity within each band for smoother gradients */
    var alpha = 0.6 + abs * 0.4;
    return "rgba(" + r + "," + g + "," + b + "," + alpha.toFixed(2) + ")";
}

function driftTextColor(value) {
    return Math.abs(value) > 0.5 ? "#ede8e3" : "#7a7268";
}

function renderDriftHeatmap(canvasId, sessions, inflections) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || sessions.length === 0) return;

    var ctx = canvas.getContext("2d");
    var container = canvas.parentElement;
    var dpr = window.devicePixelRatio || 1;

    var n = RADAR_AXES.length;        /* 11 axes */
    var cols = sessions.length;

    /* Layout constants */
    var labelWidth = 170;             /* Left axis labels */
    var headerHeight = 70;            /* Top session labels */
    var cellH = 30;
    var containerW = container.clientWidth || 800;
    var cellW = Math.max(50, Math.min(80, (containerW - labelWidth - 20) / cols));
    var totalW = labelWidth + cellW * cols + 20;
    var totalH = headerHeight + cellH * n + 10;

    /* Set canvas size accounting for DPR */
    canvas.width = totalW * dpr;
    canvas.height = totalH * dpr;
    canvas.style.width = totalW + "px";
    canvas.style.height = totalH + "px";
    ctx.scale(dpr, dpr);

    /* Store layout for click handling */
    canvas._driftLayout = {
        labelWidth: labelWidth,
        headerHeight: headerHeight,
        cellW: cellW,
        cellH: cellH,
        cols: cols,
        rows: n,
        sessions: sessions
    };

    /* Clear */
    ctx.clearRect(0, 0, totalW, totalH);

    /* Build inflection index for quick lookup */
    var inflectionCols = {};
    inflections.forEach(function (inf) {
        inflectionCols[inf.to_idx] = inf;
    });

    /* Draw session column headers (rotated) */
    ctx.save();
    ctx.font = "11px 'JetBrains Mono', monospace";
    ctx.fillStyle = "#b8b0a6";
    ctx.textAlign = "left";
    for (var c = 0; c < cols; c++) {
        var x = labelWidth + c * cellW + cellW / 2;
        var y = headerHeight - 8;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(-Math.PI / 4);
        var label = sessions[c].label || sessions[c].date || "";
        if (label.length > 18) label = label.substring(0, 18) + "...";
        ctx.fillText(label, 0, 0);
        ctx.restore();

        /* Inflection marker */
        if (inflectionCols[c]) {
            ctx.beginPath();
            ctx.arc(x, headerHeight - 2, 4, 0, Math.PI * 2);
            ctx.fillStyle = "#e8713a";
            ctx.fill();
            ctx.fillStyle = "#b8b0a6";
        }
    }
    ctx.restore();

    /* Draw axis labels (left side) and cells */
    for (var r = 0; r < n; r++) {
        var axis = RADAR_AXES[r];
        var axisName = AXIS_NAMES[axis.key] || axis.key;
        /* Use positive pole (first part before " / ") */
        var positivePole = axisName.split(" / ")[0];
        var rowY = headerHeight + r * cellH;

        /* Axis label */
        ctx.font = "12px 'Outfit', sans-serif";
        ctx.fillStyle = "#b8b0a6";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        ctx.fillText(positivePole, labelWidth - 12, rowY + cellH / 2);

        /* Cells */
        for (var c = 0; c < cols; c++) {
            var cellX = labelWidth + c * cellW;
            var val = sessions[c].resonance[axis.key] || 0;

            /* Cell background */
            ctx.fillStyle = driftColor(val);
            ctx.fillRect(cellX, rowY, cellW - 1, cellH - 1);

            /* Cell border */
            ctx.strokeStyle = "rgba(50, 45, 40, 0.5)";
            ctx.lineWidth = 0.5;
            ctx.strokeRect(cellX, rowY, cellW - 1, cellH - 1);

            /* Cell value text */
            ctx.font = "11px 'JetBrains Mono', monospace";
            ctx.fillStyle = driftTextColor(val);
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(val.toFixed(1), cellX + cellW / 2, rowY + cellH / 2);
        }
    }

    /* Click handler for axis labels → sparkline */
    canvas.onclick = function (e) {
        var rect = canvas.getBoundingClientRect();
        var mx = e.clientX - rect.left;
        var my = e.clientY - rect.top;
        var layout = canvas._driftLayout;

        /* Check if click is in the axis label area */
        if (mx < layout.labelWidth && my >= layout.headerHeight) {
            var rowIdx = Math.floor((my - layout.headerHeight) / layout.cellH);
            if (rowIdx >= 0 && rowIdx < layout.rows) {
                var axisKey = RADAR_AXES[rowIdx].key;
                toggleDriftSparkline(axisKey, sessions);
            }
        }
    };

    /* Hover cursor for axis labels */
    canvas.onmousemove = function (e) {
        var rect = canvas.getBoundingClientRect();
        var mx = e.clientX - rect.left;
        var my = e.clientY - rect.top;
        var layout = canvas._driftLayout;

        if (mx < layout.labelWidth && my >= layout.headerHeight) {
            var rowIdx = Math.floor((my - layout.headerHeight) / layout.cellH);
            canvas.style.cursor = (rowIdx >= 0 && rowIdx < layout.rows) ? "pointer" : "default";
        } else {
            canvas.style.cursor = "default";
        }
    };
}

function toggleDriftSparkline(axisKey, sessions) {
    var container = document.getElementById("drift-sparkline");
    if (!container) return;

    if (currentDriftAxis === axisKey) {
        /* Collapse */
        container.style.display = "none";
        currentDriftAxis = null;
        return;
    }

    currentDriftAxis = axisKey;
    container.style.display = "block";
    renderDriftSparkline("sparkline-canvas", sessions, axisKey);
}

function renderDriftSparkline(canvasId, sessions, axisKey) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || sessions.length === 0) return;

    var ctx = canvas.getContext("2d");
    var container = canvas.parentElement;
    var dpr = window.devicePixelRatio || 1;

    var axisName = AXIS_NAMES[axisKey] || axisKey;

    /* Layout */
    var padLeft = 60;
    var padRight = 70;
    var padTop = 40;
    var padBottom = 50;
    var totalW = container.clientWidth;
    var totalH = 220;
    var plotW = totalW - padLeft - padRight;
    var plotH = totalH - padTop - padBottom;

    canvas.width = totalW * dpr;
    canvas.height = totalH * dpr;
    canvas.style.width = totalW + "px";
    canvas.style.height = totalH + "px";
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, totalW, totalH);

    /* Extract values */
    var values = sessions.map(function (s) { return s.resonance[axisKey] || 0; });
    var lastVal = values[values.length - 1];

    /* Title */
    ctx.font = "14px 'Outfit', sans-serif";
    ctx.fillStyle = "#ede8e3";
    ctx.textAlign = "left";
    ctx.fillText(axisName, padLeft, 24);

    /* Y-axis: -1.0 to 1.0 */
    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.fillStyle = "#7a7268";
    ctx.textAlign = "right";
    var yTicks = [-1.0, -0.5, 0.0, 0.5, 1.0];
    yTicks.forEach(function (t) {
        var y = padTop + plotH * (1 - (t + 1) / 2);
        ctx.fillText(t.toFixed(1), padLeft - 8, y + 3);

        /* Grid line */
        ctx.beginPath();
        ctx.moveTo(padLeft, y);
        ctx.lineTo(padLeft + plotW, y);
        ctx.strokeStyle = t === 0 ? "rgba(50, 45, 40, 0.8)" : "rgba(50, 45, 40, 0.3)";
        ctx.lineWidth = t === 0 ? 1 : 0.5;
        if (t === 0) {
            ctx.setLineDash([4, 4]);
        }
        ctx.stroke();
        ctx.setLineDash([]);
    });

    /* Points */
    var pts = values.map(function (v, i) {
        var x = padLeft + (sessions.length === 1 ? plotW / 2 : (i / (sessions.length - 1)) * plotW);
        var y = padTop + plotH * (1 - (v + 1) / 2);
        return { x: x, y: y, val: v };
    });

    /* Smoothed bezier curve */
    var lineColor = lastVal >= 0 ? "#e8713a" : "#6b8aad";
    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";

    if (pts.length === 1) {
        /* Single point — just draw a dot */
        ctx.beginPath();
    } else if (pts.length === 2) {
        ctx.moveTo(pts[0].x, pts[0].y);
        ctx.lineTo(pts[1].x, pts[1].y);
        ctx.stroke();
    } else {
        ctx.moveTo(pts[0].x, pts[0].y);
        for (var i = 1; i < pts.length; i++) {
            var prev = pts[i - 1];
            var curr = pts[i];
            var cpx = (prev.x + curr.x) / 2;
            ctx.bezierCurveTo(cpx, prev.y, cpx, curr.y, curr.x, curr.y);
        }
        ctx.stroke();
    }

    /* Dots at each point */
    pts.forEach(function (p) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = lineColor;
        ctx.fill();
        ctx.strokeStyle = "#0f0e0d";
        ctx.lineWidth = 2;
        ctx.stroke();
    });

    /* X-axis session labels */
    ctx.font = "9px 'JetBrains Mono', monospace";
    ctx.fillStyle = "#7a7268";
    ctx.textAlign = "center";
    /* Show labels for up to 20 sessions, skip if too many */
    var step = Math.max(1, Math.ceil(sessions.length / 20));
    for (var i = 0; i < sessions.length; i += step) {
        var label = sessions[i].date || sessions[i].label || "";
        if (label.length > 8) label = label.substring(0, 8);
        ctx.save();
        ctx.translate(pts[i].x, padTop + plotH + 16);
        ctx.rotate(-Math.PI / 6);
        ctx.fillText(label, 0, 0);
        ctx.restore();
    }

    /* Current value at right end */
    ctx.font = "bold 16px 'JetBrains Mono', monospace";
    ctx.fillStyle = lineColor;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    var lastPt = pts[pts.length - 1];
    ctx.fillText(lastVal.toFixed(2), lastPt.x + 12, lastPt.y);
}
