"""ContextAssembler — shared query + packing engine for hearth_briefing and hearth_context."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from hearth.config import RESONANCE_AXES
from hearth.resonance_guide import (
    RESONANCE_GUIDE,
    estimate_tokens,
    format_resonance_guide,
)

if TYPE_CHECKING:
    from hearth.db import HearthDB

logger = logging.getLogger("hearth.context")

# Keywords that trigger inclusion of the resonance guide in context queries
_RESONANCE_KEYWORDS = {"resonance", "scoring", "axes", "guide", "session_close"}

# Safety margin: pack to 90% of budget
_SAFETY_MARGIN = 0.90

# Reserved token budgets for always-included sections
_PREAMBLE_BUDGET = 50
_TRAILING_GUIDE_BUDGET = 300


def describe_resonance(resonance: dict[str, Any]) -> str:
    """Convert a session's 11-axis resonance vector into a natural language description.

    Takes the top 3-4 most extreme axes (furthest from 0) and describes the shape.
    """
    if not resonance:
        return "no resonance data"

    # Extract axis values, skipping metadata fields
    axis_values: list[tuple[str, float]] = []
    for axis in RESONANCE_AXES:
        val = resonance.get(axis)
        if val is not None:
            axis_values.append((axis, float(val)))

    if not axis_values:
        return "no resonance data"

    # Sort by absolute value, most extreme first
    axis_values.sort(key=lambda x: abs(x[1]), reverse=True)

    # Take top 3-4 axes (those with |value| > 0.3, max 4)
    significant = [(a, v) for a, v in axis_values if abs(v) > 0.3][:4]
    if not significant:
        # All axes near zero — flat session
        return "neutral resonance profile"

    fragments: list[str] = []
    for axis, value in significant:
        entry = RESONANCE_GUIDE[axis]
        if value > 0:
            fragments.append(entry["positive_pole"].split(" — ")[0].lower())
        else:
            fragments.append(entry["negative_pole"].split(" — ")[0].lower())

    if len(fragments) == 1:
        return fragments[0]
    return ", ".join(fragments[:-1]) + " and " + fragments[-1]


class ContextAssembler:
    """Shared query + packing engine for hearth_briefing and hearth_context."""

    def __init__(self, db: HearthDB) -> None:
        self.db = db

    def assemble_briefing(
        self,
        project: str | None = None,
        token_budget: int = 2000,
    ) -> dict[str, Any]:
        """Assemble ambient briefing from all data sources.

        Returns structured dict with 'briefing' text and 'metadata'.
        Uses a bookend pattern: preamble at top, resonance guide at bottom.
        """
        effective_budget = int(token_budget * _SAFETY_MARGIN)

        # Reserve space for preamble and trailing guide
        preamble = self._build_preamble()
        trailing_guide = self._build_trailing_guide(
            effective_budget - _PREAMBLE_BUDGET
        )
        reserved = estimate_tokens(preamble) + estimate_tokens(trailing_guide)
        tier_budget = max(0, effective_budget - reserved)

        # Build tiers
        tier1 = self._build_tier1(project)
        tier1_tokens = estimate_tokens(tier1)

        sections: list[str] = [preamble, ""]

        metadata: dict[str, Any] = {
            "project": project,
            "token_budget": token_budget,
            "tiers_included": [],
        }

        if tier1_tokens <= tier_budget:
            sections.append(tier1)
            metadata["tiers_included"].append(1)
            remaining = tier_budget - tier1_tokens

            # Tier 2: tensions, drift, high-vitality memories
            if remaining > 50:
                tier2 = self._build_tier2(project, remaining)
                if tier2:
                    tier2_tokens = estimate_tokens(tier2)
                    if tier2_tokens <= remaining:
                        sections.append(tier2)
                        metadata["tiers_included"].append(2)
                        remaining -= tier2_tokens

            # Tier 3: older sessions, parked threads, cross-project
            if remaining > 50:
                tier3 = self._build_tier3(project, remaining)
                if tier3:
                    tier3_tokens = estimate_tokens(tier3)
                    if tier3_tokens <= remaining:
                        sections.append(tier3)
                        metadata["tiers_included"].append(3)
        else:
            # Budget too small for full tier 1 — include what we can
            sections.append(tier1)
            metadata["tiers_included"].append(1)

        # Always append trailing resonance guide last
        sections.append("")
        sections.append(trailing_guide)

        briefing = "\n".join(sections)
        metadata["estimated_tokens"] = estimate_tokens(briefing)
        return {"briefing": briefing, "metadata": metadata}

    def assemble_context(
        self,
        query: str,
        project: str | None = None,
        token_budget: int = 1500,
    ) -> dict[str, Any]:
        """Assemble query-specific context from all data sources.

        Searches memories, threads, tensions, and session summaries.
        Returns structured dict with 'context' text and 'metadata'.
        """
        effective_budget = int(token_budget * _SAFETY_MARGIN)
        sections: list[str] = []
        sources: list[str] = []

        query_lower = query.lower()

        # Check if query is about resonance guide
        if any(kw in query_lower for kw in _RESONANCE_KEYWORDS):
            guide = format_resonance_guide()
            guide_tokens = estimate_tokens(guide)
            if guide_tokens <= effective_budget:
                sections.append(guide)
                sources.append("resonance_guide")
                effective_budget -= guide_tokens

        # Search memories via FTS
        if effective_budget > 50:
            memory_results = self.db.fts_search(
                query, project=project, limit=5
            )
            if memory_results:
                mem_section = self._format_memory_results(memory_results)
                mem_tokens = estimate_tokens(mem_section)
                if mem_tokens <= effective_budget:
                    sections.append(mem_section)
                    sources.append("memories")
                    effective_budget -= mem_tokens

        # Search threads by title/trajectory
        if effective_budget > 50:
            thread_section = self._search_threads(query, project)
            if thread_section:
                t_tokens = estimate_tokens(thread_section)
                if t_tokens <= effective_budget:
                    sections.append(thread_section)
                    sources.append("threads")
                    effective_budget -= t_tokens

        # Search tensions by question
        if effective_budget > 50:
            tension_section = self._search_tensions(query, project)
            if tension_section:
                t_tokens = estimate_tokens(tension_section)
                if t_tokens <= effective_budget:
                    sections.append(tension_section)
                    sources.append("tensions")
                    effective_budget -= t_tokens

        # Search session summaries
        if effective_budget > 50:
            session_section = self._search_sessions(query, project)
            if session_section:
                s_tokens = estimate_tokens(session_section)
                if s_tokens <= effective_budget:
                    sections.append(session_section)
                    sources.append("sessions")
                    effective_budget -= s_tokens

        if not sections:
            context_text = f"No relevant context found for: {query}"
        else:
            context_text = "\n\n".join(sections)

        metadata: dict[str, Any] = {
            "query": query,
            "project": project,
            "token_budget": token_budget,
            "sources": sources,
            "estimated_tokens": estimate_tokens(context_text),
        }
        return {"context": context_text, "metadata": metadata}

    # ── Briefing tier builders ────────────────────────────────────────

    def _build_preamble(self) -> str:
        return (
            "At the end of this session, you will be asked to close the session "
            "with `session_close`. This requires a qualitative summary and scores "
            "on 11 resonance axes (floats from -1.0 to 1.0). The full axis "
            "definitions and scoring guide are at the end of this briefing."
        )

    def _build_trailing_guide(self, budget: int) -> str:
        return format_resonance_guide(token_budget=budget)

    def _build_tier1(self, project: str | None) -> str:
        """Recent sessions + active threads."""
        lines: list[str] = []

        # Last 3 sessions with summaries and resonance descriptions
        sessions = self.db.list_sessions(project=project, limit=3)
        if sessions:
            lines.append("## Recent Sessions")
            for s in sessions:
                summary = s.get("summary") or "no summary"
                resonance = self.db.get_resonance(s["id"])
                if resonance:
                    shape = describe_resonance(resonance)
                    lines.append(f"- {summary} ({shape})")
                else:
                    lines.append(f"- {summary}")
            lines.append("")

        # Active threads with trajectories
        threads = self.db.list_threads(project=project, status="open", limit=10)
        if threads:
            lines.append("## Active Threads")
            for t in threads:
                trajectory = t.get("trajectory") or ""
                sess_count = t.get("session_count", 0)
                tension_count = t.get("tension_count", 0)
                detail = f" — {trajectory}" if trajectory else ""
                counts = f" [{sess_count} sessions, {tension_count} tensions]"
                lines.append(f"- **{t['title']}**{detail}{counts}")
            lines.append("")

        if not lines:
            lines.append("No prior session history or threads yet.")

        return "\n".join(lines)

    def _build_tier2(self, project: str | None, budget: int) -> str:
        """Open tensions, drift summary, high-vitality memories."""
        lines: list[str] = []
        remaining = budget

        # Open tensions with perspectives
        tensions = self.db.list_tensions(project=project, limit=5)
        open_tensions = [t for t in tensions if t["status"] in ("open", "evolving")]
        if open_tensions:
            tension_lines: list[str] = ["## Open Tensions"]
            for t in open_tensions:
                status_tag = f" [{t['status']}]" if t["status"] != "open" else ""
                tension_lines.append(f"- {t['question']}{status_tag}")
                perspectives = t.get("perspectives") or []
                for p in perspectives[-2:]:  # Last 2 perspectives
                    if isinstance(p, dict):
                        tension_lines.append(f"  - {p.get('source', '?')}: {p.get('text', str(p))}")
                    else:
                        tension_lines.append(f"  - {p}")
            tension_lines.append("")
            tension_section = "\n".join(tension_lines)
            t_tokens = estimate_tokens(tension_section)
            if t_tokens <= remaining:
                lines.append(tension_section)
                remaining -= t_tokens

        # Drift summary: axis trends over recent sessions
        if remaining > 50:
            drift = self._compute_drift_summary(project)
            if drift:
                d_tokens = estimate_tokens(drift)
                if d_tokens <= remaining:
                    lines.append(drift)
                    remaining -= d_tokens

        # High-vitality memories
        if remaining > 50:
            mem_section = self._get_high_vitality_memories(project, remaining)
            if mem_section:
                lines.append(mem_section)

        return "\n".join(lines) if lines else ""

    def _build_tier3(self, project: str | None, budget: int) -> str:
        """Older sessions, parked threads, cross-project context."""
        lines: list[str] = []
        remaining = budget

        # Older sessions (skip first 3, get next 5)
        sessions = self.db.list_sessions(project=project, limit=5, offset=3)
        if sessions:
            session_lines: list[str] = ["## Earlier Sessions"]
            for s in sessions:
                summary = s.get("summary") or "no summary"
                session_lines.append(f"- {summary}")
            session_lines.append("")
            s_section = "\n".join(session_lines)
            s_tokens = estimate_tokens(s_section)
            if s_tokens <= remaining:
                lines.append(s_section)
                remaining -= s_tokens

        # Parked threads
        if remaining > 50:
            parked = self.db.list_threads(project=project, status="parked", limit=5)
            if parked:
                parked_lines: list[str] = ["## Parked Threads"]
                for t in parked:
                    trajectory = t.get("trajectory") or ""
                    detail = f" — {trajectory}" if trajectory else ""
                    parked_lines.append(f"- {t['title']}{detail}")
                parked_lines.append("")
                p_section = "\n".join(parked_lines)
                p_tokens = estimate_tokens(p_section)
                if p_tokens <= remaining:
                    lines.append(p_section)
                    remaining -= p_tokens

        # Cross-project: global high-vitality memories (only if project-scoped)
        if remaining > 50 and project is not None:
            global_mems = self._get_high_vitality_memories(None, remaining)
            if global_mems:
                lines.append(global_mems.replace(
                    "## High-Vitality Memories",
                    "## Global Memories",
                ))

        return "\n".join(lines) if lines else ""

    # ── Context search helpers ────────────────────────────────────────

    def _format_memory_results(self, memories: list[dict[str, Any]]) -> str:
        lines: list[str] = ["## Relevant Memories"]
        for m in memories:
            project_tag = f" [{m.get('project', 'global')}]" if m.get("project") else ""
            category = m.get("category", "general")
            lines.append(f"- ({category}{project_tag}) {m['content']}")
        return "\n".join(lines)

    def _search_threads(self, query: str, project: str | None) -> str:
        """Search thread titles and trajectories for keyword matches."""
        threads = self.db.list_threads(project=project, limit=20)
        query_words = set(query.lower().split())
        matches: list[dict[str, Any]] = []

        for t in threads:
            text = f"{t['title']} {t.get('trajectory', '')}".lower()
            if any(w in text for w in query_words):
                matches.append(t)

        if not matches:
            return ""

        lines: list[str] = ["## Related Threads"]
        for t in matches[:5]:
            status = t.get("status", "open")
            trajectory = t.get("trajectory") or ""
            detail = f" — {trajectory}" if trajectory else ""
            lines.append(f"- [{status}] **{t['title']}**{detail}")
        return "\n".join(lines)

    def _search_tensions(self, query: str, project: str | None) -> str:
        """Search tension questions for keyword matches."""
        tensions = self.db.list_tensions(project=project, limit=20)
        query_words = set(query.lower().split())
        matches: list[dict[str, Any]] = []

        for t in tensions:
            text = t["question"].lower()
            if any(w in text for w in query_words):
                matches.append(t)

        if not matches:
            return ""

        lines: list[str] = ["## Related Tensions"]
        for t in matches[:5]:
            status = t.get("status", "open")
            lines.append(f"- [{status}] {t['question']}")
        return "\n".join(lines)

    def _search_sessions(self, query: str, project: str | None) -> str:
        """Search session summaries for keyword matches."""
        sessions = self.db.list_sessions(project=project, limit=20)
        query_words = set(query.lower().split())
        matches: list[dict[str, Any]] = []

        for s in sessions:
            summary = (s.get("summary") or "").lower()
            if summary and any(w in summary for w in query_words):
                matches.append(s)

        if not matches:
            return ""

        lines: list[str] = ["## Related Sessions"]
        for s in matches[:5]:
            summary = s.get("summary") or "no summary"
            lines.append(f"- {summary}")
        return "\n".join(lines)

    # ── Data helpers ──────────────────────────────────────────────────

    def _compute_drift_summary(self, project: str | None) -> str:
        """Compute simple directional trends over recent sessions."""
        sessions = self.db.list_sessions(project=project, limit=10)
        if len(sessions) < 3:
            return ""

        # Collect resonance vectors
        vectors: list[dict[str, float]] = []
        for s in reversed(sessions):  # Chronological order
            res = self.db.get_resonance(s["id"])
            if res:
                vectors.append({
                    axis: float(res.get(axis, 0.0)) for axis in RESONANCE_AXES
                })

        if len(vectors) < 3:
            return ""

        # Compute trend per axis: difference between avg of last 3 and avg of first 3
        n = min(3, len(vectors))
        early = vectors[:n]
        recent = vectors[-n:]

        trends: list[tuple[str, float]] = []
        for axis in RESONANCE_AXES:
            early_avg = sum(v[axis] for v in early) / n
            recent_avg = sum(v[axis] for v in recent) / n
            shift = recent_avg - early_avg
            if abs(shift) > 0.2:  # Only report meaningful shifts
                trends.append((axis, shift))

        if not trends:
            return ""

        trends.sort(key=lambda x: abs(x[1]), reverse=True)
        lines: list[str] = ["## Drift Trends"]
        for axis, shift in trends[:5]:
            direction = "increasing" if shift > 0 else "decreasing"
            entry = RESONANCE_GUIDE[axis]
            pole = entry["positive_pole"] if shift > 0 else entry["negative_pole"]
            lines.append(
                f"- {entry['name']}: {direction} ({shift:+.2f}) — trending toward {pole.split(' — ')[0].lower()}"
            )
        lines.append("")
        return "\n".join(lines)

    def _get_high_vitality_memories(
        self, project: str | None, budget: int
    ) -> str:
        """Get memories with highest vitality scores."""
        # Use list_memories sorted by vitality (we filter non-archived, active lifecycle)
        memories = self.db.list_memories(
            project=project, limit=10, include_archived=False
        )
        # Sort by vitality_score descending, filter for active/fading
        vitality_mems = [
            m for m in memories
            if m.get("lifecycle_state") in ("active", "fading")
            and m.get("vitality_score", 0) > 0.3
        ]
        vitality_mems.sort(key=lambda m: m.get("vitality_score", 0), reverse=True)

        if not vitality_mems:
            return ""

        lines: list[str] = ["## High-Vitality Memories"]
        tokens_used = estimate_tokens("## High-Vitality Memories")
        for m in vitality_mems[:5]:
            line = f"- ({m.get('category', 'general')}) {m['content']}"
            line_tokens = estimate_tokens(line)
            if tokens_used + line_tokens > budget:
                break
            lines.append(line)
            tokens_used += line_tokens

        if len(lines) == 1:  # Only header, no memories fit
            return ""

        return "\n".join(lines)
