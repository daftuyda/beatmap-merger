import os
import argparse
from pydub import AudioSegment

def parse_osu(filepath):
    """
    Parse an .osu file into its sections as a dict of lists of lines.
    """
    sections = {}
    current = None
    with open(filepath, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if line.startswith('[') and line.endswith(']'):
                current = line.strip('[]')
                sections[current] = []
            else:
                if current is not None:
                    sections[current].append(line)
    return sections


def write_osu(sections, output_path):
    """
    Write merged sections back into an .osu file.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for sec in ['General', 'Metadata', 'Difficulty', 'Events', 'TimingPoints', 'HitObjects']:
            if sec in sections and sections[sec]:
                f.write(f'[{sec}]\n')
                for line in sections[sec]:
                    f.write(line + '\n')
                f.write('\n')


def merge_beatmaps(osu_paths, audio_paths, output_osu, output_audio, hp, od, cs, ar):
    """
    Merge multiple .osu beatmaps and their audio files into one compilation.
    osu_paths and audio_paths should be in matching, sorted order.
    """
    audio_segments = []
    merged = {
        'General': [], 'Metadata': [], 'Difficulty': [],
        'Events': [], 'TimingPoints': [], 'HitObjects': []
    }
    cumulative_offset = 0

    for idx, osu in enumerate(osu_paths):
        sec = parse_osu(osu)
        # Load and append audio by direct file
        audio_file = audio_paths[idx]
        sound = AudioSegment.from_file(audio_file)
        audio_segments.append(sound)

        # Initialize merged General/Metadata/Difficulty/Events from the first beatmap
        if idx == 0:
            base_general = [l for l in sec['General'] if not l.startswith('AudioFilename')]
            base_general.append(f'AudioFilename: {os.path.basename(output_audio)}')
            merged['General'] = base_general
            merged['Metadata'] = sec.get('Metadata', [])
            merged['Events'] = sec.get('Events', [])
            # Difficulty: override HP, CS, OD, AR
            diff_lines = [l for l in sec.get('Difficulty', [])
                          if not any(l.startswith(f'{d}:') for d in ['HPDrainRate','CircleSize','OverallDifficulty','ApproachRate'])]
            diff_lines.extend([
                f'HPDrainRate: {hp}',
                f'CircleSize: {cs}',
                f'OverallDifficulty: {od}',
                f'ApproachRate: {ar}',
            ])
            merged['Difficulty'] = diff_lines

        # Offset and collect timing points
        for tp in sec.get('TimingPoints', []):
            if tp and not tp.startswith('//'):
                parts = tp.split(',')
                t = float(parts[0]) + cumulative_offset
                merged['TimingPoints'].append(','.join([str(int(t))] + parts[1:]))

        # Offset and collect hit objects
        for ho in sec.get('HitObjects', []):
            if ho and not ho.startswith('//'):
                parts = ho.split(',')
                parts[2] = str(int(parts[2]) + cumulative_offset)
                merged['HitObjects'].append(','.join(parts))

        cumulative_offset += len(sound)

    # Sort all by timestamp
    merged['TimingPoints'].sort(key=lambda x: int(x.split(',')[0]))
    merged['HitObjects'].sort(key=lambda x: int(x.split(',')[2]))

    # Write outputs
    write_osu(merged, output_osu)
    combined = sum(audio_segments)
    combined.export(output_audio, format=os.path.splitext(output_audio)[1].lstrip('.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge osu beatmaps in a folder into a compilation map')
    parser.add_argument('input_dir', help='Directory containing numbered .osu and matching audio files')
    parser.add_argument('--output-osu', default='merged.osu', help='Output .osu filename')
    parser.add_argument('--output-audio', default='merged_audio.mp3', help='Output audio filename')
    parser.add_argument('--hp', type=float, default=5.0, help='HP Drain Rate')
    parser.add_argument('--od', type=float, default=8.0, help='Overall Difficulty')
    parser.add_argument('--cs', type=float, default=4.0, help='Circle Size')
    parser.add_argument('--ar', type=float, default=9.0, help='Approach Rate')
    args = parser.parse_args()

    # Scan directory for osu and audio files
    files = os.listdir(args.input_dir)
    osu_files = sorted([f for f in files if f.lower().endswith('.osu')],
                       key=lambda x: int(os.path.splitext(x)[0]))
    audio_files = sorted([f for f in files if os.path.splitext(f)[1].lower() in ['.mp3','.wav','.ogg']],
                         key=lambda x: int(os.path.splitext(x)[0]))
    if len(osu_files) != len(audio_files):
        raise RuntimeError('Number of .osu and audio files do not match.')

    osu_paths = [os.path.join(args.input_dir, f) for f in osu_files]
    audio_paths = [os.path.join(args.input_dir, f) for f in audio_files]

    merge_beatmaps(osu_paths, audio_paths,
                   args.output_osu, args.output_audio,
                   args.hp, args.od, args.cs, args.ar)
