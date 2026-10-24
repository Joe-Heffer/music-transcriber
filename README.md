# Bass stem transcriber

A small, reproducible workflow for turning isolated bass stems (WAV) into MIDI
with Spotify's [Basic Pitch](https://github.com/spotify/basic-pitch). The MIDI
is then opened in MuseScore to produce notation and tab by hand.

## Requirements

- Linux (x86-64)
- [uv](https://docs.astral.sh/uv/), which also downloads the Python 3.10
  interpreter used by the project
- `make`
- [MuseScore](https://musescore.org/) 4, for notation and tab. It is a GUI
  application and is not installed by this project.

### Why Python 3.10 and TensorFlow Lite

Basic Pitch 0.4.0 chooses its inference backend from the Python version. On
Linux with Python 3.11 or later it requires full TensorFlow below 2.15.1. That
is a very large install, and it has no wheels for Python 3.12 or later, so it
cannot be installed with the system Python 3.14. On Python 3.10 it uses
`tflite-runtime` instead: a small runtime that runs the same model
(`nmp.tflite`) with no TensorFlow at all. `numpy<2` is pinned because
`tflite-runtime` 2.14 is built against NumPy 1.x, and `setuptools<81` is pinned
because `resampy` still imports `pkg_resources`.

## Setup

```sh
make setup
```

This creates `.venv` with Python 3.10 and installs the pinned dependencies from
`requirements.txt`. To change a dependency, edit `requirements.in` and run
`make freeze`, then `make setup`.

## Layout

| Folder     | Contents                                         |
|------------|--------------------------------------------------|
| `stems/`   | input WAV files (git ignores all audio)          |
| `midi/`    | Basic Pitch output: `.mid` plus a `.json` sidecar |
| `scores/`  | MuseScore files and exports                      |
| `scripts/` | helper code                                      |

## Workflow

1. Put one or more isolated bass stems in `stems/`, for example
   `stems/song-bass.wav`.
2. Transcribe every WAV in `stems/`:

   ```sh
   make transcribe
   ```

   Pass extra options through `ARGS`:

   ```sh
   make transcribe ARGS="--onset-threshold 0.7 --min-note-ms 80"
   ```

   You can also run the script on specific files:

   ```sh
   .venv/bin/python scripts/transcribe.py stems/song-bass.wav --out-dir midi
   ```

3. Each input `name.wav` produces `midi/name.mid` and `midi/name.json`. The
   sidecar records the settings, model, Basic Pitch version, note count and
   pitch range, so different runs can be compared. Rename or move a pair
   before re-running if you want to keep it, because outputs are overwritten.
4. Open the MIDI in MuseScore (see below) and save the score to `scores/`.
5. `make clean` removes everything in `midi/`.

## Settings

The defaults are set for a monophonic line on a 4-string bass:

| Option                   | Default  | Notes                                                       |
|--------------------------|----------|-------------------------------------------------------------|
| `--onset-threshold`      | 0.6      | Raise to cut ghost or spurious notes; lower if real notes go missing (Basic Pitch default 0.5) |
| `--frame-threshold`      | 0.4      | Raise to shorten or split smeared notes; lower if sustained notes break up (default 0.3) |
| `--min-note-ms`          | 120      | Discards blips. Lower it (to around 60–80) for fast sixteenth-note lines |
| `--min-freq`             | 41.2 Hz  | E1, the open low E string                                   |
| `--max-freq`             | 392 Hz   | G4, about the top of the fretboard                          |
| `--no-melodia-trick`     | (on)     | Turns off Basic Pitch's melodia post-processing             |
| `--multiple-pitch-bends` | (off)    | Lets overlapping notes carry their own pitch bends          |
| `--tempo`                | 120      | Tempo written into the MIDI. Set it to the song's tempo so MuseScore's bar lines line up |

Run `.venv/bin/python scripts/transcribe.py --help` for the full list.

## MuseScore notes

- Open the MIDI with File, Open. MIDI import applies default quantisation, so
  check rhythm and note spelling.
- For tab, add a linked 4-string bass tab staff instead of converting the bass
  staff.
- If tab notes all land on one string, the notes are probably an octave too
  high. Bass is written an octave above where it sounds.
- Fret positions are chosen by MuseScore, so check them against how the line
  was actually played.
