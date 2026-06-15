import json
import subprocess
from fractions import Fraction
from pathlib import Path

SUPPORTED = {'.mp4', '.mov', '.mkv', '.avi', '.m4v'}


def probe(clip_path: Path) -> dict:
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_streams', '-show_format', str(clip_path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)

    video = next(
        s for s in data['streams']
        if s['codec_type'] == 'video'
        and not s.get('disposition', {}).get('attached_pic')
    )
    audio = next((s for s in data['streams'] if s['codec_type'] == 'audio'), None)

    return {
        'path': str(clip_path.resolve()),
        'duration': float(data['format']['duration']),
        'fps': float(Fraction(video['r_frame_rate'])),
        'width': video['width'],
        'height': video['height'],
        'has_audio': audio is not None,
        'size_mb': round(int(data['format']['size']) / 1024 / 1024, 1),
    }


def find_clips(input_dir: Path) -> list[Path]:
    clips = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED)
    if not clips:
        raise ValueError(f"No supported video files found in {input_dir}")
    return clips
