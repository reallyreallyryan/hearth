"""Tests for hearth.transcribe and hearth ingest CLI command."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from click.testing import CliRunner

from hearth.cli import cli
from hearth.transcribe import (
    LocalTranscriber,
    Segment,
    TranscriptResult,
    TranscriptionError,
    VALID_MODELS,
    SUPPORTED_EXTENSIONS,
)


@pytest.fixture
def wav_file(tmp_path) -> Path:
    """Create a minimal WAV file with a 440Hz tone (1 second, 16kHz mono)."""
    filepath = tmp_path / "test.wav"
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0
    n_samples = int(sample_rate * duration)

    with wave.open(str(filepath), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wf.writeframes(struct.pack("<h", sample))

    return filepath


@pytest.fixture
def empty_wav(tmp_path) -> Path:
    """Create an empty file with .wav extension."""
    filepath = tmp_path / "empty.wav"
    filepath.touch()
    return filepath


# ── is_available ──────────────────────────────────────────────────


class TestIsAvailable:
    def test_returns_true_when_installed(self) -> None:
        assert LocalTranscriber.is_available() is True


# ── Initialization ─────────────────────────────────────────────────


class TestInit:
    def test_default_values(self) -> None:
        t = LocalTranscriber()
        assert t.model_size == "base"
        assert t.model_dir is None
        assert t.device == "auto"
        assert t.compute_type == "default"
        assert t._model is None

    def test_custom_values(self) -> None:
        t = LocalTranscriber(
            model_size="small",
            model_dir="/tmp/models",
            device="cpu",
            compute_type="int8",
        )
        assert t.model_size == "small"
        assert t.model_dir == "/tmp/models"
        assert t.device == "cpu"
        assert t.compute_type == "int8"


# ── Input Validation ──────────────────────────────────────────────


class TestInputValidation:
    def test_file_not_found(self) -> None:
        t = LocalTranscriber()
        with pytest.raises(TranscriptionError, match="not found"):
            t.transcribe("/nonexistent/audio.wav")

    def test_unsupported_format(self, tmp_path) -> None:
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("not audio")
        t = LocalTranscriber()
        with pytest.raises(TranscriptionError, match="Unsupported audio format"):
            t.transcribe(bad_file)

    def test_empty_file(self, empty_wav) -> None:
        t = LocalTranscriber()
        with pytest.raises(TranscriptionError, match="empty"):
            t.transcribe(empty_wav)

    def test_invalid_model_name(self, wav_file) -> None:
        t = LocalTranscriber(model_size="nonexistent-model")
        with pytest.raises(TranscriptionError, match="Unknown model"):
            t.transcribe(wav_file)


# ── Transcription with Mocked Model ─────────────────────────────


def _make_mock_model():
    """Create a mock WhisperModel that returns predictable segments."""
    mock_model = MagicMock()

    mock_seg1 = MagicMock()
    mock_seg1.start = 0.0
    mock_seg1.end = 2.5
    mock_seg1.text = " Hello world"

    mock_seg2 = MagicMock()
    mock_seg2.start = 2.5
    mock_seg2.end = 5.0
    mock_seg2.text = " This is a test"

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.duration = 5.0

    mock_model.transcribe.return_value = (
        iter([mock_seg1, mock_seg2]),
        mock_info,
    )
    return mock_model


class TestTranscribeWithMock:
    def test_returns_transcript_result(self, wav_file) -> None:
        t = LocalTranscriber(model_size="base")
        t._model = _make_mock_model()

        result = t.transcribe(wav_file)

        assert isinstance(result, TranscriptResult)
        assert result.text == "Hello world This is a test"
        assert result.language == "en"
        assert result.duration == 5.0
        assert result.model_used == "base"
        assert result.processing_time >= 0
        assert len(result.segments) == 2

    def test_segments_have_valid_timestamps(self, wav_file) -> None:
        t = LocalTranscriber(model_size="base")
        t._model = _make_mock_model()

        result = t.transcribe(wav_file)

        for seg in result.segments:
            assert isinstance(seg, Segment)
            assert seg.start >= 0
            assert seg.end > seg.start
            assert len(seg.text) > 0

    def test_segments_are_ordered(self, wav_file) -> None:
        t = LocalTranscriber(model_size="base")
        t._model = _make_mock_model()

        result = t.transcribe(wav_file)

        for i in range(1, len(result.segments)):
            assert result.segments[i].start >= result.segments[i - 1].start

    def test_text_is_concatenation_of_segments(self, wav_file) -> None:
        t = LocalTranscriber(model_size="base")
        t._model = _make_mock_model()

        result = t.transcribe(wav_file)

        expected = " ".join(seg.text for seg in result.segments)
        assert result.text == expected


# ── Integration Test (requires model download) ──────────────────


@pytest.mark.slow
def test_transcribe_real_model(wav_file) -> None:
    """End-to-end test with real tiny model. Marked slow — skipped by default."""
    t = LocalTranscriber(model_size="tiny")
    result = t.transcribe(wav_file)
    assert isinstance(result, TranscriptResult)
    assert result.language
    assert result.duration > 0
    assert result.processing_time > 0
    assert result.model_used == "tiny"


# ── Ingest CLI Command ──────────────────────────────────────────


def _mock_transcript_result():
    """Create a TranscriptResult for mocking."""
    return TranscriptResult(
        text="Hello world This is a test",
        segments=[
            Segment(start=0.0, end=2.5, text="Hello world"),
            Segment(start=2.5, end=5.0, text="This is a test"),
        ],
        language="en",
        duration=5.0,
        model_used="base",
        processing_time=0.5,
    )


class TestIngestCommand:
    def test_ingest_stores_memory(self, wav_file, tmp_db) -> None:
        runner = CliRunner()
        mock_result = _mock_transcript_result()

        with patch("hearth.cli.load_config") as mock_config, \
             patch("hearth.transcribe.LocalTranscriber") as MockTranscriber, \
             patch("hearth.embeddings.OllamaEmbedder") as MockEmbedder:

            # Config points to tmp_db
            cfg = mock_config.return_value
            cfg.db_path = tmp_db.db_path
            cfg.transcription.default_model = "base"
            cfg.transcription.model_dir = None
            cfg.transcription.device = "auto"
            cfg.transcription.compute_type = "default"
            cfg.ollama_base_url = "http://localhost:11434"
            cfg.embedding.model = "nomic-embed-text"
            cfg.embedding.dimensions = 768

            # Transcriber returns mock result
            MockTranscriber.is_available.return_value = True
            mock_transcriber = MockTranscriber.return_value
            mock_transcriber.transcribe.return_value = mock_result

            # Embedder returns None (Ollama unavailable)
            mock_embedder = MockEmbedder.return_value
            mock_embed = AsyncMock(return_value=None)
            mock_embedder.embed = mock_embed

            result = runner.invoke(cli, ["ingest", str(wav_file)])

        assert result.exit_code == 0
        assert "Stored memory" in result.output

    def test_ingest_db_not_initialized(self, wav_file, tmp_path) -> None:
        runner = CliRunner()

        with patch("hearth.cli.load_config") as mock_config:
            cfg = mock_config.return_value
            cfg.db_path = tmp_path / "nonexistent.db"

            result = runner.invoke(cli, ["ingest", str(wav_file)])

        assert result.exit_code == 1
        assert "not initialized" in result.output

    def test_ingest_no_faster_whisper(self, wav_file, tmp_db) -> None:
        runner = CliRunner()

        with patch("hearth.cli.load_config") as mock_config, \
             patch("hearth.transcribe.LocalTranscriber") as MockTranscriber:

            cfg = mock_config.return_value
            cfg.db_path = tmp_db.db_path
            MockTranscriber.is_available.return_value = False

            result = runner.invoke(cli, ["ingest", str(wav_file)])

        assert result.exit_code == 1
        assert "faster-whisper" in result.output

    def test_ingest_with_tags(self, wav_file, tmp_db) -> None:
        runner = CliRunner()
        mock_result = _mock_transcript_result()

        with patch("hearth.cli.load_config") as mock_config, \
             patch("hearth.transcribe.LocalTranscriber") as MockTranscriber, \
             patch("hearth.embeddings.OllamaEmbedder") as MockEmbedder:

            cfg = mock_config.return_value
            cfg.db_path = tmp_db.db_path
            cfg.transcription.default_model = "base"
            cfg.transcription.model_dir = None
            cfg.transcription.device = "auto"
            cfg.transcription.compute_type = "default"
            cfg.ollama_base_url = "http://localhost:11434"
            cfg.embedding.model = "nomic-embed-text"
            cfg.embedding.dimensions = 768

            MockTranscriber.is_available.return_value = True
            mock_transcriber = MockTranscriber.return_value
            mock_transcriber.transcribe.return_value = mock_result

            mock_embedder = MockEmbedder.return_value
            mock_embedder.embed = AsyncMock(return_value=None)

            result = runner.invoke(cli, [
                "ingest", str(wav_file), "--tags", "meeting,planning"
            ])

        assert result.exit_code == 0
        assert "Stored memory" in result.output
