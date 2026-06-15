import subprocess
from pathlib import Path


def detect_shots(clip_path: Path, threshold: float = 0.35) -> list[float]:
    """Return timestamps (seconds) of scene-change frames."""
    result = subprocess.run(
        [
            'ffmpeg', '-i', str(clip_path),
            '-vf', f"select='gt(scene,{threshold})',metadata=print:file=-",
            '-an', '-f', 'null', '-',
        ],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    timestamps = []
    for line in output.splitlines():
        if 'pts_time:' in line:
            try:
                ts = float(line.split('pts_time:')[1].split()[0])
                timestamps.append(round(ts, 3))
            except (ValueError, IndexError):
                continue
    return timestamps


def cuts_to_segments(cuts: list[float], duration: float) -> list[dict]:
    """Convert a list of cut timestamps into [{"start", "end", "duration"}, ...] segments."""
    boundaries = [0.0] + cuts + [duration]
    segments = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        segments.append({
            'start': round(start, 3),
            'end': round(end, 3),
            'duration': round(end - start, 3),
        })
    return segments
