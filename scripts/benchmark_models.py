#!/usr/bin/env python3
"""Benchmark Whisper model sizes on a sample audio file.

Usage:
    python scripts/benchmark_models.py path/to/audio.wav
    python scripts/benchmark_models.py path/to/audio.wav --models tiny,base,small
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hearth.transcribe import LocalTranscriber, TranscriptionError

BENCHMARK_MODELS = ["tiny", "base", "small", "medium", "large-v3-turbo"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Whisper model sizes")
    parser.add_argument("audio_file", type=Path, help="Audio file to transcribe")
    parser.add_argument(
        "--models",
        default=",".join(BENCHMARK_MODELS),
        help=f"Comma-separated model sizes (default: {','.join(BENCHMARK_MODELS)})",
    )
    args = parser.parse_args()

    if not args.audio_file.exists():
        print(f"Error: {args.audio_file} not found")
        sys.exit(1)

    models = [m.strip() for m in args.models.split(",")]

    print(f"Audio file: {args.audio_file}")
    print(f"Models: {', '.join(models)}")
    print()
    print(f"{'Model':<20} {'Time (s)':<12} {'Speed':<10} {'Language':<10} {'Text preview'}")
    print("-" * 90)

    for model_name in models:
        try:
            transcriber = LocalTranscriber(model_size=model_name)
            result = transcriber.transcribe(args.audio_file)
            speed = f"{result.duration / result.processing_time:.1f}x" if result.processing_time > 0 else "N/A"
            preview = result.text[:60] + "..." if len(result.text) > 60 else result.text
            print(f"{model_name:<20} {result.processing_time:<12.2f} {speed:<10} {result.language:<10} {preview}")
        except TranscriptionError as e:
            print(f"{model_name:<20} ERROR: {e}")
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(1)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
