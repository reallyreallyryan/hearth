"""Local audio transcription using faster-whisper (CTranslate2 backend)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("hearth.transcribe")

VALID_MODELS = (
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large-v1",
    "large-v2",
    "large-v3",
    "large",
    "distil-small.en",
    "distil-medium.en",
    "distil-large-v2",
    "distil-large-v3",
    "large-v3-turbo",
    "turbo",
)

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}


@dataclass
class Segment:
    """A timestamped segment of transcribed text."""

    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    """Complete transcription result."""

    text: str
    segments: list[Segment]
    language: str
    duration: float
    model_used: str
    processing_time: float


class TranscriptionError(Exception):
    """Raised when transcription fails."""


class LocalTranscriber:
    """Transcribes audio files locally using faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        model_dir: str | None = None,
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        self.model_size = model_size
        self.model_dir = model_dir
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _get_model(self):
        """Lazy-load the WhisperModel. Downloads on first use."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise TranscriptionError(
                    "faster-whisper is not installed. "
                    "Install it with: pip install hearth-memory[transcribe]"
                )

            if self.model_size not in VALID_MODELS:
                raise TranscriptionError(
                    f"Unknown model '{self.model_size}'. "
                    f"Valid models: {', '.join(VALID_MODELS)}"
                )

            logger.info(
                "Loading Whisper model '%s' (device=%s, compute_type=%s)",
                self.model_size,
                self.device,
                self.compute_type,
            )

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.model_dir,
            )
        return self._model

    @staticmethod
    def is_available() -> bool:
        """Check if faster-whisper is installed and importable."""
        try:
            from faster_whisper import WhisperModel  # noqa: F401

            return True
        except ImportError:
            return False

    def transcribe(self, audio_path: str | Path) -> TranscriptResult:
        """Transcribe an audio file. Returns TranscriptResult."""
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        suffix = audio_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise TranscriptionError(
                f"Unsupported audio format '{suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        if audio_path.stat().st_size == 0:
            raise TranscriptionError(f"Audio file is empty: {audio_path}")

        model = self._get_model()

        start_time = time.monotonic()

        try:
            segments_iter, info = model.transcribe(
                str(audio_path),
                beam_size=5,
                vad_filter=True,
            )
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

        segments = []
        text_parts = []
        for seg in segments_iter:
            segments.append(
                Segment(
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=seg.text.strip(),
                )
            )
            text_parts.append(seg.text.strip())

        processing_time = time.monotonic() - start_time

        return TranscriptResult(
            text=" ".join(text_parts),
            segments=segments,
            language=info.language,
            duration=round(info.duration, 3),
            model_used=self.model_size,
            processing_time=round(processing_time, 3),
        )
