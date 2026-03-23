"""Configuration loading and defaults for Hearth."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

HEARTH_DIR = Path.home() / "hearth"
DEFAULT_DB_PATH = HEARTH_DIR / "hearth.db"
DEFAULT_CONFIG_PATH = HEARTH_DIR / "config.yaml"

VALID_CATEGORIES = {"general", "learning", "pattern", "reference", "decision"}
VALID_SOURCES = {"user", "assistant", "system"}
VALID_PROJECT_STATUSES = {"active", "paused", "completed", "archived"}


@dataclass
class EmbeddingConfig:
    provider: str = "ollama"
    model: str = "nomic-embed-text"
    dimensions: int = 768


@dataclass
class SearchConfig:
    default_limit: int = 10
    semantic_weight: float = 0.6
    fts_weight: float = 0.4


@dataclass
class HearthConfig:
    version: str = "0.1.0"
    db_path: Path = field(default_factory=lambda: DEFAULT_DB_PATH)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    ollama_base_url: str = "http://localhost:11434"


def load_config(config_path: Path | None = None) -> HearthConfig:
    """Load config from YAML file, falling back to defaults for missing keys."""
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config = HearthConfig()

    if not config_path.exists():
        return config

    raw = yaml.safe_load(config_path.read_text()) or {}

    hearth_section = raw.get("hearth", {})
    if "version" in hearth_section:
        config.version = hearth_section["version"]
    if "db_path" in hearth_section:
        db_path = Path(hearth_section["db_path"])
        if not db_path.is_absolute():
            db_path = config_path.parent / db_path
        config.db_path = db_path.resolve()

    models = raw.get("models", {})
    emb = models.get("embedding", {})
    if "provider" in emb:
        config.embedding.provider = emb["provider"]
    if "model" in emb:
        config.embedding.model = emb["model"]
    if "dimensions" in emb:
        config.embedding.dimensions = int(emb["dimensions"])

    server = raw.get("server", {})
    if "host" in server:
        config.ollama_base_url = f"http://{server['host']}:11434"

    search = raw.get("search", {})
    if "default_limit" in search:
        config.search.default_limit = int(search["default_limit"])
    if "semantic_weight" in search:
        config.search.semantic_weight = float(search["semantic_weight"])
    if "fts_weight" in search:
        config.search.fts_weight = float(search["fts_weight"])

    return config


def save_default_config(config_path: Path) -> None:
    """Write default config.yaml to disk."""
    data = {
        "hearth": {
            "version": "0.1.0",
            "db_path": "./hearth.db",
        },
        "models": {
            "embedding": {
                "provider": "ollama",
                "model": "nomic-embed-text",
                "dimensions": 768,
            },
        },
        "search": {
            "default_limit": 10,
            "semantic_weight": 0.6,
            "fts_weight": 0.4,
        },
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
