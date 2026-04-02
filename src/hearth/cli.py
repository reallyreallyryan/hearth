"""Hearth CLI: init, serve, status, remember, search."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import click

from hearth import __version__
from hearth.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_DB_PATH,
    HEARTH_DIR,
    load_config,
    save_default_config,
)

# All CLI output to stderr so it doesn't interfere with MCP stdio
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    stream=sys.stderr,
)


def _echo(msg: str) -> None:
    """Print to stderr (stdout reserved for MCP stdio)."""
    click.echo(msg, err=True)


def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS.mmm for segment display."""
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:06.3f}"


@click.group()
@click.version_option(__version__, prog_name="hearth")
def cli() -> None:
    """Hearth - persistent AI memory system."""
    pass


@cli.command()
@click.option("--no-models", is_flag=True, help="Skip Ollama model check/pull (cloud-only mode)")
def init(no_models: bool) -> None:
    """Initialize Hearth: create database, config, and check Ollama."""
    _echo("Initializing Hearth...\n")

    # 1. Check disk space
    _check_disk_space(HEARTH_DIR.parent)

    # 2. Create directory (owner-only access)
    HEARTH_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(HEARTH_DIR, stat.S_IRWXU)  # 700
    _echo(f"  Directory: {HEARTH_DIR}")

    # 3. Write config
    if DEFAULT_CONFIG_PATH.exists():
        _echo(f"  Config:    {DEFAULT_CONFIG_PATH} (already exists)")
    else:
        save_default_config(DEFAULT_CONFIG_PATH)
        _echo(f"  Config:    {DEFAULT_CONFIG_PATH} (created)")

    # 4. Initialize database
    config = load_config()
    from hearth.db import HearthDB

    db = HearthDB(config.db_path)
    db.init_db()
    db.close()
    # Restrict database file permissions (owner read/write only)
    if config.db_path.exists():
        os.chmod(config.db_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
    _echo(f"  Database:  {config.db_path}")

    # 5. Check Ollama (or skip)
    _echo("")
    if no_models:
        _echo("  Ollama:    skipped (--no-models)")
        _echo("             Semantic search requires embeddings.")
        _echo("             Install Ollama later or configure a cloud provider in config.yaml.")
    else:
        _check_ollama(config.embedding.model)

    # 6. Print connection instructions
    # Use full path to hearth binary — Claude Desktop / LM Studio have limited PATHs
    hearth_bin = shutil.which("hearth") or "hearth"

    _echo("\n" + "=" * 50)
    _echo("Hearth is ready!\n")
    _echo("Start the MCP server:")
    _echo(f"  {hearth_bin} serve\n")
    _echo("Add to Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json):")
    _echo(json.dumps(
        {"mcpServers": {"hearth": {"command": hearth_bin, "args": ["serve"]}}},
        indent=2,
    ))
    _echo("\nOr for LM Studio (~/.lmstudio/mcp.json):")
    _echo(json.dumps(
        {"mcpServers": {"hearth": {"command": hearth_bin, "args": ["serve"]}}},
        indent=2,
    ))


def _check_disk_space(path: Path) -> None:
    """Warn if disk space is low on the volume containing path."""
    try:
        usage = shutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)
        if free_gb < 1.0:
            _echo(f"  WARNING:   Low disk space ({free_gb:.1f} GB free)")
            _echo("             Hearth needs ~300MB for the embedding model.")
        else:
            _echo(f"  Disk:      {free_gb:.1f} GB free")
    except OSError:
        pass  # Non-critical — skip if we can't check


# Known model sizes for user-facing display
_MODEL_SIZES = {
    "nomic-embed-text": "~274MB",
}


def _check_ollama(model: str) -> None:
    """Check Ollama availability and pull embedding model if needed."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            _echo("  Ollama:    not running (start with 'ollama serve')")
            return
    except FileNotFoundError:
        _echo("  Ollama:    not installed")
        _echo("             Install from https://ollama.ai")
        _echo("             Hearth will work without it (FTS-only search)")
        return
    except subprocess.TimeoutExpired:
        _echo("  Ollama:    not responding")
        return

    # Check if model is available
    if model in result.stdout or f"{model}:" in result.stdout:
        _echo(f"  Ollama:    {model} (ready)")
    else:
        size = _MODEL_SIZES.get(model, "")
        size_str = f" ({size})" if size else ""
        _echo(f"  Ollama:    pulling {model}{size_str}...")
        pull = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True, text=True, timeout=300,
        )
        if pull.returncode == 0:
            _echo(f"  Ollama:    {model} (pulled successfully)")
        else:
            _echo(f"  Ollama:    failed to pull {model}")
            _echo(f"             Run 'ollama pull {model}' manually")


@cli.command()
def serve() -> None:
    """Start the Hearth MCP server (stdio transport)."""
    from hearth.server import run_server

    run_server()


@cli.command()
def status() -> None:
    """Show database stats, Ollama status, and version info."""
    config = load_config()

    _echo(f"Hearth v{__version__}")
    _echo(f"Database: {config.db_path}")

    if not config.db_path.exists():
        _echo("  Status: not initialized (run 'hearth init')")
        return

    from hearth.db import HearthDB
    from hearth.embeddings import OllamaEmbedder

    db = HearthDB(config.db_path)
    db.init_db()
    stats = db.get_stats()

    _echo(f"\nMemories:   {stats['total_memories']} active, {stats['archived_memories']} archived")
    _echo(f"Embeddings: {stats['total_embeddings']} ({stats['pending_embeddings']} pending)")
    _echo(f"Projects:   {stats['active_projects']} active")

    if stats["by_category"]:
        _echo("\nBy category:")
        for cat, count in sorted(stats["by_category"].items()):
            _echo(f"  {cat}: {count}")

    if stats["by_project"]:
        _echo("\nBy project:")
        for proj, count in sorted(stats["by_project"].items()):
            _echo(f"  {proj}: {count}")

    # Check Ollama
    embedder = OllamaEmbedder(
        base_url=config.ollama_base_url,
        model=config.embedding.model,
    )
    available = asyncio.run(embedder.check_available())
    _echo(f"\nOllama: {'available' if available else 'unavailable'} ({config.embedding.model})")

    db.close()


@cli.command()
@click.argument("content")
@click.option("--category", "-c", default="general", help="Memory category")
@click.option("--project", "-p", default=None, help="Project name")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def remember(content: str, category: str, project: str | None, tags: str | None) -> None:
    """Store a memory from the command line."""
    config = load_config()

    if not config.db_path.exists():
        _echo("Hearth not initialized. Run 'hearth init' first.")
        raise SystemExit(1)

    from hearth.db import HearthDB
    from hearth.embeddings import OllamaEmbedder

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    db = HearthDB(config.db_path)
    db.init_db()

    try:
        memory = db.store_memory(content, category, project, tag_list, source="user")
    except ValueError as e:
        _echo(f"Error: {e}")
        db.close()
        raise SystemExit(1)

    # Attempt embedding
    embedder = OllamaEmbedder(
        base_url=config.ollama_base_url,
        model=config.embedding.model,
        dimensions=config.embedding.dimensions,
    )
    result = asyncio.run(embedder.embed(content))
    if result:
        db.store_embedding(memory["id"], result.embedding)
        _echo(f"Stored memory {memory['id'][:8]}... with embedding")
    else:
        _echo(f"Stored memory {memory['id'][:8]}... (no embedding — Ollama unavailable)")

    db.close()


@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--limit", "-n", default=10, help="Max results")
def search(query: str, project: str | None, category: str | None, limit: int) -> None:
    """Search memories from the command line."""
    config = load_config()

    if not config.db_path.exists():
        _echo("Hearth not initialized. Run 'hearth init' first.")
        raise SystemExit(1)

    from hearth.db import HearthDB
    from hearth.embeddings import OllamaEmbedder
    from hearth.search import hybrid_search

    db = HearthDB(config.db_path)
    db.init_db()
    embedder = OllamaEmbedder(
        base_url=config.ollama_base_url,
        model=config.embedding.model,
        dimensions=config.embedding.dimensions,
    )

    results = asyncio.run(
        hybrid_search(query, db, embedder, project=project, category=category, limit=limit, config=config.search)
    )

    if not results:
        _echo("No results found.")
    else:
        for i, r in enumerate(results, 1):
            mem = r.memory
            _echo(f"\n[{i}] ({r.match_type}, score: {r.score})")
            _echo(f"    {mem['content'][:200]}")
            meta = []
            if mem.get("category"):
                meta.append(f"category={mem['category']}")
            if mem.get("project"):
                meta.append(f"project={mem['project']}")
            if mem.get("tags"):
                meta.append(f"tags={mem['tags']}")
            if meta:
                _echo(f"    [{', '.join(meta)}]")
            _echo(f"    id={mem['id'][:8]}... created={mem['created_at']}")

    db.close()


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("--model", "-m", default=None, help="Model size (tiny, base, small, medium, large-v3, turbo)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--segments", is_flag=True, help="Show timestamped segments")
def transcribe(audio_file: str, model: str | None, as_json: bool, segments: bool) -> None:
    """Transcribe an audio file using local Whisper model."""
    from hearth.transcribe import LocalTranscriber, TranscriptionError

    config = load_config()
    model_size = model or config.transcription.default_model

    if not LocalTranscriber.is_available():
        _echo("Error: faster-whisper is not installed.")
        _echo("Install it with: pip install hearth-memory[transcribe]")
        raise SystemExit(1)

    _echo(f"Transcribing {audio_file} with model '{model_size}'...")

    transcriber = LocalTranscriber(
        model_size=model_size,
        model_dir=config.transcription.model_dir,
        device=config.transcription.device,
        compute_type=config.transcription.compute_type,
    )

    try:
        result = transcriber.transcribe(audio_file)
    except TranscriptionError as e:
        _echo(f"Error: {e}")
        raise SystemExit(1)

    if as_json:
        output = {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "model": result.model_used,
            "processing_time": result.processing_time,
        }
        if segments:
            output["segments"] = [
                {"start": s.start, "end": s.end, "text": s.text}
                for s in result.segments
            ]
        _echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        _echo(f"\nLanguage: {result.language}")
        _echo(f"Duration: {result.duration:.1f}s")
        _echo(f"Processing time: {result.processing_time:.1f}s")
        speed = result.duration / result.processing_time if result.processing_time > 0 else 0
        _echo(f"Speed: {speed:.1f}x realtime")
        _echo(f"\n{'=' * 50}")

        if segments:
            for seg in result.segments:
                timestamp = f"[{_fmt_time(seg.start)} -> {_fmt_time(seg.end)}]"
                _echo(f"  {timestamp}  {seg.text}")
        else:
            _echo(result.text)


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("--model", "-m", default=None, help="Model size (tiny, base, small, medium, large-v3, turbo)")
@click.option("--project", "-p", default=None, help="Project name")
@click.option("--category", "-c", default="general", help="Memory category")
@click.option("--tags", "-t", default=None, help="Comma-separated tags (added to auto-generated tags)")
def ingest(audio_file: str, model: str | None, project: str | None, category: str, tags: str | None) -> None:
    """Transcribe an audio file and store it as a memory."""
    from hearth.transcribe import LocalTranscriber, TranscriptionError

    config = load_config()

    if not config.db_path.exists():
        _echo("Hearth not initialized. Run 'hearth init' first.")
        raise SystemExit(1)

    if not LocalTranscriber.is_available():
        _echo("Error: faster-whisper is not installed.")
        _echo("Install it with: pip install hearth-memory[transcribe]")
        raise SystemExit(1)

    model_size = model or config.transcription.default_model
    _echo(f"Transcribing {audio_file} with model '{model_size}'...")

    transcriber = LocalTranscriber(
        model_size=model_size,
        model_dir=config.transcription.model_dir,
        device=config.transcription.device,
        compute_type=config.transcription.compute_type,
    )

    try:
        result = transcriber.transcribe(audio_file)
    except TranscriptionError as e:
        _echo(f"Error: {e}")
        raise SystemExit(1)

    _echo(f"  Language: {result.language}, Duration: {result.duration:.1f}s, "
          f"Speed: {result.duration / result.processing_time:.1f}x realtime")

    # Build tags: auto-generated metadata + user-provided
    audio_name = Path(audio_file).name
    auto_tags = [
        f"audio:{audio_name}",
        f"duration:{result.duration:.1f}s",
        f"model:{result.model_used}",
        f"lang:{result.language}",
    ]
    if tags:
        auto_tags.extend(t.strip() for t in tags.split(","))

    # Store memory
    from hearth.db import HearthDB
    from hearth.embeddings import OllamaEmbedder

    db = HearthDB(config.db_path)
    db.init_db()

    try:
        memory = db.store_memory(
            result.text,
            category=category,
            project=project,
            tags=auto_tags,
            source="transcription",
        )
    except ValueError as e:
        _echo(f"Error: {e}")
        db.close()
        raise SystemExit(1)

    # Generate and store embedding
    embedder = OllamaEmbedder(
        base_url=config.ollama_base_url,
        model=config.embedding.model,
        dimensions=config.embedding.dimensions,
    )
    embed_result = asyncio.run(embedder.embed(result.text))
    if embed_result:
        db.store_embedding(memory["id"], embed_result.embedding)
        _echo(f"  Stored memory {memory['id'][:8]}... with embedding")
    else:
        _echo(f"  Stored memory {memory['id'][:8]}... (no embedding — Ollama unavailable)")

    _echo(f"\n  \"{result.text[:100]}{'...' if len(result.text) > 100 else ''}\"")
    _echo(f"\nDone. Search with: hearth search \"<query>\"")

    db.close()


@cli.command()
@click.option("--port", "-p", default=8274, help="Port to serve on")
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
def ui(port: int, open_browser: bool) -> None:
    """Start the Hearth web dashboard."""
    config = load_config()

    if not config.db_path.exists():
        _echo("Hearth not initialized. Run 'hearth init' first.")
        raise SystemExit(1)

    try:
        from hearth.web.app import run_app
    except ImportError:
        _echo("Web UI dependencies not installed.")
        _echo("Install with: pip install hearth-memory[ui]")
        raise SystemExit(1)

    _echo(f"Starting Hearth dashboard at http://localhost:{port}")

    if open_browser:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")

    run_app(port=port)
