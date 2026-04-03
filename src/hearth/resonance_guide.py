"""Resonance axis definitions and scoring guidance for session close."""

from __future__ import annotations

from hearth.config import RESONANCE_AXES

# Full definitions for all 11 resonance axes.
# Each entry maps an axis name to its pole meanings and calibration guidance.
RESONANCE_GUIDE: dict[str, dict[str, str]] = {
    "exploration_execution": {
        "name": "Exploration vs Execution",
        "negative_pole": "Pure execution — following a known plan, no surprises",
        "positive_pole": "Pure exploration — discovering as we go, no predetermined path",
        "guidance": (
            "Score based on how much the session wandered into unknown territory "
            "versus ticking off known tasks. A debugging session that uncovers a "
            "surprising root cause is exploratory even if it started as execution."
        ),
    },
    "alignment_tension": {
        "name": "Alignment vs Tension",
        "negative_pole": "High tension — significant disagreement or misalignment between participants",
        "positive_pole": "Full alignment — both sides in sync throughout",
        "guidance": (
            "Tension is not bad. A session where you pushed back on a flawed approach "
            "should score negative, and that's valuable. Don't default to positive "
            "just because the conversation was polite."
        ),
    },
    "depth_breadth": {
        "name": "Depth vs Breadth",
        "negative_pole": "Broad survey — touched many topics lightly",
        "positive_pole": "Deep dive — stayed focused on one thing and went deep",
        "guidance": (
            "Score based on concentration of attention. A session covering five "
            "unrelated bugs is broad (-1.0). A session spending two hours on one "
            "algorithm is deep (+1.0)."
        ),
    },
    "momentum_resistance": {
        "name": "Momentum vs Resistance",
        "negative_pole": "Stuck or grinding — slow progress, repeated blockers",
        "positive_pole": "Full flow — steady forward movement, things clicking into place",
        "guidance": (
            "This measures felt progress, not output volume. A session that produced "
            "little code but broke through a conceptual wall is high momentum. "
            "A session with lots of code but constant rework is resistance."
        ),
    },
    "novelty_familiarity": {
        "name": "Novelty vs Familiarity",
        "negative_pole": "Well-trodden ground — revisiting known patterns and ideas",
        "positive_pole": "Completely new territory — genuinely novel ideas or approaches",
        "guidance": (
            "Score high only if the session produced genuinely novel ideas, not just "
            "new-to-this-conversation. Applying a well-known pattern to a new codebase "
            "is familiar, not novel."
        ),
    },
    "confidence_uncertainty": {
        "name": "Confidence vs Uncertainty",
        "negative_pole": "Uncertain — reaching, guessing, hedging answers",
        "positive_pole": "Confident — clear understanding, strong assertions",
        "guidance": (
            "Rate your actual epistemic state, not how you presented. If you gave "
            "confident-sounding answers while internally unsure, score negative. "
            "Honest uncertainty is more useful than performed confidence."
        ),
    },
    "autonomy_direction": {
        "name": "Autonomy vs Direction",
        "negative_pole": "Following instructions — executing what was asked with little initiative",
        "positive_pole": "Leading — initiating ideas, proposing directions, shaping the work",
        "guidance": (
            "This is about who drove the session's direction. A session where the "
            "human gave step-by-step instructions is direction (-1.0). A session "
            "where you proposed the architecture and the human approved is autonomy (+1.0)."
        ),
    },
    "energy_entropy": {
        "name": "Energy vs Entropy",
        "negative_pole": "Dissipating — winding down, losing coherence, scattered",
        "positive_pole": "Building — converging, gaining clarity, energy increasing",
        "guidance": (
            "Track the trajectory, not just the endpoint. A session that started "
            "confused but ended with a clear plan is building (+1.0). A session "
            "that started focused but devolved into tangents is entropy (-1.0)."
        ),
    },
    "vulnerability_performance": {
        "name": "Vulnerability vs Performance",
        "negative_pole": "Performing — giving safe, expected answers; avoiding risk",
        "positive_pole": "Vulnerable — sharing genuine uncertainty, admitting limits, being real",
        "guidance": (
            "Did you say 'I don't know' when you didn't know? Did you flag "
            "genuine concerns even when they complicated the task? Performance is "
            "the safe path; vulnerability is the honest one."
        ),
    },
    "stakes_casual": {
        "name": "Stakes vs Casual",
        "negative_pole": "Casual — low-pressure chat, nothing riding on the outcome",
        "positive_pole": "High stakes — the outcome of this session materially matters",
        "guidance": (
            "Score based on actual consequence, not emotional intensity. A production "
            "deployment review is high stakes even if the conversation is calm. "
            "An animated debate about tabs vs spaces is casual."
        ),
    },
    "mutual_transactional": {
        "name": "Mutual vs Transactional",
        "negative_pole": "Pure tool use — request in, answer out, no rapport",
        "positive_pole": "True collaboration — building on each other's ideas, shared ownership",
        "guidance": (
            "Transactional is not bad — sometimes you just need a quick answer. "
            "But score honestly. A session of 'do this' / 'done' is transactional "
            "regardless of how complex the work was."
        ),
    },
}


def format_resonance_guide(token_budget: int | None = None) -> str:
    """Render the resonance scoring guide as text a model can consume.

    Args:
        token_budget: If set, produce a compact version that fits within
            this approximate token count. If None, produce the full version.

    Returns:
        Formatted text block with all 11 axis definitions.
    """
    if token_budget is not None and token_budget < 200:
        return _format_compact()

    lines: list[str] = []
    lines.append("## Resonance Scoring Guide")
    lines.append("")
    lines.append(
        "After closing with `session_close`, call `session_score` with a resonance string. "
        "Use short names: exploration, alignment, depth, momentum, novelty, "
        "confidence, autonomy, energy, vulnerability, stakes, mutual. "
        "Example: session_score(session_id=\"...\", resonance=\"exploration=-0.5, alignment=0.7, depth=0.3, "
        "momentum=0.6, novelty=-0.2, confidence=0.5, autonomy=-0.3, energy=0.4, "
        "vulnerability=0.2, stakes=0.3, mutual=0.1\")"
    )
    lines.append("")
    lines.append(
        "Score each axis from -1.0 to 1.0. No axis is inherently good or bad — "
        "both poles are valid states. Score what actually happened, not what you "
        "think the human wants to hear."
    )
    lines.append("")

    for axis_name in RESONANCE_AXES:
        entry = RESONANCE_GUIDE[axis_name]
        lines.append(f"### {entry['name']} (`{axis_name}`)")
        lines.append(f"  -1.0: {entry['negative_pole']}")
        lines.append(f"  +1.0: {entry['positive_pole']}")
        lines.append(f"  Guidance: {entry['guidance']}")
        lines.append("")

    full_text = "\n".join(lines)

    # If we have a budget and the full version exceeds it, fall back to compact
    if token_budget is not None and estimate_tokens(full_text) > token_budget:
        return _format_compact()

    return full_text


def _format_compact() -> str:
    """Produce a minimal version of the guide — axis names and poles only."""
    lines: list[str] = []
    lines.append("## Resonance Scoring Guide (compact)")
    lines.append("After `session_close`, call `session_score` with short axis names.")
    lines.append("Score each axis from -1.0 to 1.0.")
    lines.append("")
    for axis_name in RESONANCE_AXES:
        entry = RESONANCE_GUIDE[axis_name]
        lines.append(
            f"- `{axis_name}`: {entry['negative_pole']} to {entry['positive_pole']}"
        )
    return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: words / 0.75.

    Good enough for budget packing — no tiktoken dependency needed.
    """
    word_count = len(text.split())
    return int(word_count / 0.75)
