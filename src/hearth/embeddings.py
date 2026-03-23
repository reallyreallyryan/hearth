"""Ollama embedding generation with graceful degradation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from hearth.db import HearthDB

logger = logging.getLogger("hearth.embeddings")


@dataclass
class EmbeddingResult:
    embedding: list[float]
    model: str
    dimensions: int


class OllamaEmbedder:
    """Generate embeddings via Ollama API. Degrades gracefully if unavailable."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dimensions: int = 768,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self._available: bool | None = None

    async def check_available(self) -> bool:
        """Check if Ollama is running and the embedding model is available."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/api/tags", timeout=5.0
                )
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check for model name (with or without :latest tag)
                available = any(
                    m == self.model or m.startswith(f"{self.model}:")
                    for m in models
                )
                self._available = available
                if not available:
                    logger.warning(
                        "Ollama is running but model '%s' not found. "
                        "Available models: %s",
                        self.model,
                        ", ".join(models),
                    )
                return available
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            logger.warning("Ollama not available: %s", e)
            self._available = False
            return False

    async def embed(self, text: str) -> EmbeddingResult | None:
        """Generate embedding for a single text. Returns None if unavailable."""
        if self._available is False:
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": text},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if not embeddings:
                    logger.warning("Ollama returned empty embeddings")
                    return None

                vec = embeddings[0]
                self._available = True
                return EmbeddingResult(
                    embedding=vec,
                    model=self.model,
                    dimensions=len(vec),
                )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Ollama embedding failed: %s", e)
            self._available = False
            return None
        except (httpx.HTTPStatusError, KeyError, IndexError) as e:
            logger.warning("Ollama embedding error: %s", e)
            return None

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult | None]:
        """Embed multiple texts. Uses Ollama batch API."""
        if self._available is False or not texts:
            return [None] * len(texts)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": texts},
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])

                results: list[EmbeddingResult | None] = []
                for i, text in enumerate(texts):
                    if i < len(embeddings):
                        vec = embeddings[i]
                        results.append(EmbeddingResult(
                            embedding=vec,
                            model=self.model,
                            dimensions=len(vec),
                        ))
                    else:
                        results.append(None)
                self._available = True
                return results
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Ollama batch embedding failed: %s", e)
            self._available = False
            return [None] * len(texts)
        except (httpx.HTTPStatusError, KeyError) as e:
            logger.warning("Ollama batch embedding error: %s", e)
            return [None] * len(texts)

    async def process_pending(self, db: HearthDB) -> int:
        """Process all memories missing embeddings. Returns count processed."""
        pending = db.get_pending_embeddings()
        if not pending:
            return 0

        logger.info("Processing %d pending embeddings", len(pending))

        # Batch in groups of 32
        processed = 0
        batch_size = 32
        for i in range(0, len(pending), batch_size):
            batch = pending[i : i + batch_size]
            texts = [m["content"] for m in batch]
            results = await self.embed_batch(texts)

            for mem, result in zip(batch, results):
                if result is not None:
                    try:
                        db.store_embedding(mem["id"], result.embedding)
                        processed += 1
                    except Exception as e:
                        logger.warning(
                            "Failed to store embedding for %s: %s", mem["id"], e
                        )

            # If Ollama went down mid-batch, stop
            if self._available is False:
                logger.warning(
                    "Ollama went unavailable during batch processing. "
                    "Processed %d/%d embeddings.",
                    processed,
                    len(pending),
                )
                break

        logger.info("Processed %d/%d pending embeddings", processed, len(pending))
        return processed
