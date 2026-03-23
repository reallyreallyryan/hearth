"""Hybrid search: FTS5 + semantic (vec0) with weighted score merging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hearth.config import SearchConfig
    from hearth.db import HearthDB
    from hearth.embeddings import OllamaEmbedder

logger = logging.getLogger("hearth.search")


@dataclass
class SearchResult:
    memory: dict[str, Any]
    score: float
    match_type: str  # "hybrid", "fts", "semantic"


async def hybrid_search(
    query: str,
    db: HearthDB,
    embedder: OllamaEmbedder,
    project: str | None = None,
    category: str | None = None,
    limit: int = 10,
    config: SearchConfig | None = None,
) -> list[SearchResult]:
    """Execute hybrid search combining FTS5 and semantic results."""
    if config is None:
        from hearth.config import SearchConfig
        config = SearchConfig()

    # FTS5 search (always available)
    fts_results = db.fts_search(query, project=project, category=category, limit=limit * 2)

    # Semantic search (may fail gracefully)
    vec_results: list[tuple[str, float]] = []
    query_embedding = await embedder.embed(query)
    if query_embedding is not None:
        # Over-fetch for post-filtering
        raw_vec = db.vec_search(query_embedding.embedding, limit=limit * 3)
        # Post-filter by project and category
        vec_results = _post_filter_vec_results(raw_vec, db, project, category)

    # Merge results
    if fts_results and vec_results:
        return _merge_results(fts_results, vec_results, db, config, limit)
    elif fts_results:
        return _fts_only_results(fts_results, limit)
    elif vec_results:
        return _semantic_only_results(vec_results, db, limit)
    else:
        return []


def _post_filter_vec_results(
    vec_results: list[tuple[str, float]],
    db: HearthDB,
    project: str | None,
    category: str | None,
) -> list[tuple[str, float]]:
    """Filter vec0 results by project/category (vec0 can't do WHERE filters)."""
    if project is None and category is None:
        return vec_results

    filtered: list[tuple[str, float]] = []
    for memory_id, distance in vec_results:
        mem = db.get_memory(memory_id)
        if mem is None or mem["archived"]:
            continue
        if project is not None and mem["project"] != project:
            # Allow global memories (project=None) in project-scoped searches
            if mem["project"] is not None:
                continue
        if category is not None and mem["category"] != category:
            continue
        filtered.append((memory_id, distance))
    return filtered


def _normalize_scores(scores: list[float]) -> list[float]:
    """Min-max normalize scores to [0, 1] range. Higher = better."""
    if not scores:
        return []
    if len(scores) == 1:
        return [1.0]
    min_s, max_s = min(scores), max(scores)
    if min_s == max_s:
        return [1.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) for s in scores]


def _merge_results(
    fts_results: list[dict[str, Any]],
    vec_results: list[tuple[str, float]],
    db: HearthDB,
    config: SearchConfig,
    limit: int,
) -> list[SearchResult]:
    """Merge FTS5 and vec0 results with weighted scoring."""
    # Build FTS score map (negate BM25 so higher = better)
    fts_scores_raw = [-r.get("fts_rank", 0.0) for r in fts_results]
    fts_normalized = _normalize_scores(fts_scores_raw)
    fts_map: dict[str, tuple[dict[str, Any], float]] = {}
    for result, norm_score in zip(fts_results, fts_normalized):
        fts_map[result["id"]] = (result, norm_score)

    # Build vec score map (invert distance so higher = better similarity)
    vec_distances = [d for _, d in vec_results]
    # Cosine distance: 0 = identical, 2 = opposite. Convert to similarity.
    vec_similarities = [max(0.0, 1.0 - d) for d in vec_distances]
    vec_normalized = _normalize_scores(vec_similarities)
    vec_map: dict[str, float] = {}
    for (memory_id, _), norm_score in zip(vec_results, vec_normalized):
        vec_map[memory_id] = norm_score

    # Merge: compute final scores
    all_ids = set(fts_map.keys()) | set(vec_map.keys())
    scored: list[tuple[str, float, str]] = []

    for mid in all_ids:
        fts_score = fts_map.get(mid, (None, 0.0))[1] if mid in fts_map else 0.0
        sem_score = vec_map.get(mid, 0.0)

        if mid in fts_map and mid in vec_map:
            final = config.fts_weight * fts_score + config.semantic_weight * sem_score
            match_type = "hybrid"
        elif mid in fts_map:
            final = config.fts_weight * fts_score
            match_type = "fts"
        else:
            final = config.semantic_weight * sem_score
            match_type = "semantic"

        scored.append((mid, final, match_type))

    scored.sort(key=lambda x: x[1], reverse=True)

    results: list[SearchResult] = []
    for mid, score, match_type in scored[:limit]:
        if mid in fts_map:
            mem = fts_map[mid][0]
            # Remove internal fts_rank from output
            mem.pop("fts_rank", None)
        else:
            mem = db.get_memory(mid)
            if mem is None:
                continue
        results.append(SearchResult(memory=mem, score=round(score, 4), match_type=match_type))

    return results


def _fts_only_results(
    fts_results: list[dict[str, Any]],
    limit: int,
) -> list[SearchResult]:
    """Convert FTS results to SearchResults when no semantic search available."""
    scores = [-r.get("fts_rank", 0.0) for r in fts_results]
    normalized = _normalize_scores(scores)
    results: list[SearchResult] = []
    for result, score in zip(fts_results[:limit], normalized[:limit]):
        result.pop("fts_rank", None)
        results.append(SearchResult(memory=result, score=round(score, 4), match_type="fts"))
    return results


def _semantic_only_results(
    vec_results: list[tuple[str, float]],
    db: HearthDB,
    limit: int,
) -> list[SearchResult]:
    """Convert vec results to SearchResults when FTS returned nothing."""
    similarities = [max(0.0, 1.0 - d) for _, d in vec_results]
    normalized = _normalize_scores(similarities)
    results: list[SearchResult] = []
    for (memory_id, _), score in zip(vec_results[:limit], normalized[:limit]):
        mem = db.get_memory(memory_id)
        if mem is None:
            continue
        results.append(SearchResult(memory=mem, score=round(score, 4), match_type="semantic"))
    return results
