# osu Beatmap Merger

A simple Python script to merge multiple osu! beatmaps and their audio tracks into a single compilation map.

## Features

* Reads numbered `.osu` files and matching audio files (`1.osu`, `1.mp3`, `2.osu`, `2.mp3`, etc.) from a folder.
* Concatenates all audio files in order.
* Offsets timing points and hit objects to place each map correctly.
* Allows setting unified difficulty parameters (HP, OD, CS, AR).
* Normalizes slider velocities by preserving timing-point inheritance.

## Requirements

* Python 3.6+
* [pydub](https://github.com/jiaaro/pydub)
* `ffmpeg` or `avlib` installed on your system (for audio processing)

Install dependencies:

```bash
pip install pydub
# Ensure ffmpeg is available in your PATH
```

## Usage

```bash
python osu_beatmap_merger.py <input_dir> [options]
```

* `<input_dir>`: Directory containing paired, numbered beatmaps and audio files.

### Options

| Flag             | Description                                | Default            |
| ---------------- | ------------------------------------------ | ------------------ |
| `--output-osu`   | Output filename for the merged `.osu` map  | `merged.osu`       |
| `--output-audio` | Output filename for the merged audio track | `merged_audio.mp3` |
| `--hp`           | HP Drain Rate                              | `5.0`              |
| `--od`           | Overall Difficulty                         | `8.0`              |
| `--cs`           | Circle Size                                | `4.0`              |
| `--ar`           | Approach Rate                              | `9.0`              |

### Example

```bash
python osu_beatmap_merger.py ./maps \
  --output-osu compilation.osu \
  --output-audio compilation.mp3 \
  --hp 6.5 --od 9.0 --cs 4.0 --ar 9.5
```

This will read `maps/1.osu` + `maps/1.mp3`, `maps/2.osu` + `maps/2.mp3`, etc., and produce a single `compilation.osu` and `compilation.mp3`.

## How It Works

1. **Parsing `.osu` files**: Extracts sections (General, Metadata, Difficulty, Events, TimingPoints, HitObjects).
2. **Audio Concatenation**: Uses `pydub` to load and sum audio segments sequentially.
3. **Offset Calculation**: Adjusts each map’s timestamps by the cumulative duration of previous audio tracks.
4. **Difficulty Override**: Replaces HP/CS/OD/AR values from the first map with user-specified settings.
5. **Output**: Writes the merged beatmap and exports the combined audio.

## Troubleshooting

* **Mismatched file counts**: Ensure the number of `.osu` and audio files in the folder are equal and numbered consecutively.
* **Codec errors**: Verify `ffmpeg` is correctly installed and accessible.