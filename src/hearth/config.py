"""Configuration loading and defaults for Hearth."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

HEARTH_DIR = Path.home() / "hearth"
DEFAULT_DB_PATH = HEARTH_DIR / "hearth.db"
DEFAULT_CONFIG_PATH = HEARTH_DIR / "config.yaml"

VALID_CATEGORIES = {"general", "learning", "pattern", "reference", "decision"}
VALID_SOURCES = {"user", "assistant", "system", "transcription"}
VALID_PROJECT_STATUSES = {"active", "paused", "completed", "archived"}
VALID_THREAD_STATUSES = {"open", "parked", "resolved", "abandoned"}
VALID_TENSION_STATUSES = {"open", "evolving", "resolved", "dissolved"}
VALID_LIFECYCLE_STATES = {"active", "fading", "review", "archived"}

RESONANCE_AXES = (
    "exploration_execution",
    "alignment_tension",
    "depth_breadth",
    "momentum_resistance",
    "novelty_familiarity",
    "confidence_uncertainty",
    "autonomy_direction",
    "energy_entropy",
    "vulnerability_performance",
    "stakes_casual",
    "mutual_transactional",
)


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
class TranscriptionConfig:
    default_model: str = "base"
    model_dir: str | None = None
    device: str = "auto"
    compute_type: str = "default"


@dataclass
class VitalityConfig:
    retrieval_weight: float = 0.33
    linkage_weight: float = 0.33
    age_weight: float = 0.34
    active_threshold: float = 0.5
    review_threshold: float = 0.25
    grace_period_sessions: int = 10
    compute_every_n_closes: int = 5


@dataclass
class HearthConfig:
    version: str = "0.4.0"
    db_path: Path = field(default_factory=lambda: DEFAULT_DB_PATH)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    vitality: VitalityConfig = field(default_factory=VitalityConfig)
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

    transcription = raw.get("transcription", {})
    if "default_model" in transcription:
        config.transcription.default_model = transcription["default_model"]
    if "model_dir" in transcription:
        model_dir = transcription["model_dir"]
        if model_dir:
            p = Path(model_dir)
            if not p.is_absolute():
                p = config_path.parent / p
            config.transcription.model_dir = str(p.resolve())
    if "device" in transcription:
        config.transcription.device = transcription["device"]
    if "compute_type" in transcription:
        config.transcription.compute_type = transcription["compute_type"]

    vitality = raw.get("vitality", {})
    if "retrieval_weight" in vitality:
        config.vitality.retrieval_weight = float(vitality["retrieval_weight"])
    if "linkage_weight" in vitality:
        config.vitality.linkage_weight = float(vitality["linkage_weight"])
    if "age_weight" in vitality:
        config.vitality.age_weight = float(vitality["age_weight"])
    if "active_threshold" in vitality:
        config.vitality.active_threshold = float(vitality["active_threshold"])
    if "review_threshold" in vitality:
        config.vitality.review_threshold = float(vitality["review_threshold"])
    if "grace_period_sessions" in vitality:
        config.vitality.grace_period_sessions = int(vitality["grace_period_sessions"])
    if "compute_every_n_closes" in vitality:
        config.vitality.compute_every_n_closes = int(vitality["compute_every_n_closes"])

    return config


def save_default_config(config_path: Path) -> None:
    """Write default config.yaml to disk."""
    data = {
        "hearth": {
            "version": "0.4.0",
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
        "transcription": {
            "default_model": "base",
            "device": "auto",
            "compute_type": "default",
        },
        "vitality": {
            "retrieval_weight": 0.33,
            "linkage_weight": 0.33,
            "age_weight": 0.34,
            "active_threshold": 0.5,
            "review_threshold": 0.25,
            "grace_period_sessions": 10,
            "compute_every_n_closes": 5,
        },
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
