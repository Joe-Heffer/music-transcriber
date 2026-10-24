#!/usr/bin/env python3
"""Transcribe isolated bass stems (WAV) to MIDI with Spotify's Basic Pitch.

The defaults suit a monophonic bass line on a 4-string bass: the pitch range
is restricted to roughly E1 to G4, the onset and frame thresholds are raised
above Basic Pitch's own defaults to cut spurious notes, and very short notes
are discarded.

For each input, a MIDI file and a JSON sidecar recording the settings used
are written to the output folder, both named after the input file.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Low E on a 4-string bass (E1) and roughly the top of the fretboard (G4).
E1_HZ = 41.20
G4_HZ = 392.00


def midi_to_name(pitch: int) -> str:
    """Return the scientific pitch name for a MIDI note number, e.g. 28 -> E1."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[pitch % 12]}{pitch // 12 - 1}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe bass stems (WAV) to MIDI with Basic Pitch.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("wav", nargs="+", type=Path, help="one or more WAV files")
    parser.add_argument(
        "--onset-threshold",
        type=float,
        default=0.6,
        help="confidence needed to start a note (Basic Pitch default is 0.5)",
    )
    parser.add_argument(
        "--frame-threshold",
        type=float,
        default=0.4,
        help="confidence needed to sustain a note (Basic Pitch default is 0.3)",
    )
    parser.add_argument(
        "--min-note-ms",
        type=float,
        default=120.0,
        help="discard notes shorter than this, in milliseconds",
    )
    parser.add_argument(
        "--min-freq",
        type=float,
        default=E1_HZ,
        help="lowest pitch to keep, in Hz (E1)",
    )
    parser.add_argument(
        "--max-freq",
        type=float,
        default=G4_HZ,
        help="highest pitch to keep, in Hz (G4)",
    )
    parser.add_argument(
        "--no-melodia-trick",
        dest="melodia_trick",
        action="store_false",
        help="disable Basic Pitch's melodia post-processing",
    )
    parser.add_argument(
        "--multiple-pitch-bends",
        action="store_true",
        help="allow overlapping notes to carry their own pitch bends",
    )
    parser.add_argument(
        "--tempo", type=float, default=120.0, help="tempo written into the MIDI file"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "midi",
        help="folder for MIDI files and JSON sidecars",
    )
    return parser.parse_args(argv)


def settings_from(args: argparse.Namespace) -> dict:
    return {
        "onset_threshold": args.onset_threshold,
        "frame_threshold": args.frame_threshold,
        "minimum_note_length_ms": args.min_note_ms,
        "minimum_frequency_hz": args.min_freq,
        "maximum_frequency_hz": args.max_freq,
        "melodia_trick": args.melodia_trick,
        "multiple_pitch_bends": args.multiple_pitch_bends,
        "midi_tempo": args.tempo,
    }


def print_settings(settings: dict, model_path: Path, out_dir: Path) -> None:
    print("Basic Pitch settings:")
    width = max(len(key) for key in settings)
    for key, value in settings.items():
        print(f"  {key:<{width}}  {value}")
    print(f"  {'model':<{width}}  {model_path.name}")
    print(f"  {'output folder':<{width}}  {out_dir}")
    print()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Check every input before loading the model, so a typo fails quickly.
    bad = [p for p in args.wav if not p.is_file() or p.suffix.lower() != ".wav"]
    if bad:
        for path in bad:
            print(f"error: not a WAV file: {path}", file=sys.stderr)
        return 1

    # Basic Pitch warns about every backend that is not installed, and
    # resampy about pkg_resources; neither matters here.
    logging.getLogger().setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=UserWarning)

    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import Model, predict

    model_path = Path(ICASSP_2022_MODEL_PATH)
    settings = settings_from(args)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print_settings(settings, model_path, out_dir)

    # Load the model once and reuse it for every file.
    model = Model(model_path)

    for wav in args.wav:
        _, midi_data, note_events = predict(
            wav,
            model,
            onset_threshold=args.onset_threshold,
            frame_threshold=args.frame_threshold,
            minimum_note_length=args.min_note_ms,
            minimum_frequency=args.min_freq,
            maximum_frequency=args.max_freq,
            multiple_pitch_bends=args.multiple_pitch_bends,
            melodia_trick=args.melodia_trick,
            midi_tempo=args.tempo,
        )

        midi_path = out_dir / f"{wav.stem}.mid"
        midi_data.write(str(midi_path))

        pitches = [int(event[2]) for event in note_events]
        sidecar = {
            "input": str(wav.resolve()),
            "midi": str(midi_path.resolve()),
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "basic_pitch_version": version("basic-pitch"),
            "model": str(model_path),
            "settings": settings,
            "note_count": len(note_events),
            "lowest_note": midi_to_name(min(pitches)) if pitches else None,
            "highest_note": midi_to_name(max(pitches)) if pitches else None,
        }
        json_path = midi_path.with_suffix(".json")
        json_path.write_text(json.dumps(sidecar, indent=2) + "\n")

        span = f", {sidecar['lowest_note']} to {sidecar['highest_note']}" if pitches else ""
        print(f"{wav} -> {midi_path} ({len(note_events)} notes{span})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
