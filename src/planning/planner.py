import json
import re
from pathlib import Path

import anthropic

STYLE_PROFILE = """
You are editing in the style of "ruder_dk", a YouTube gaming/vlog creator with these rules:

PACING:
- Vlog/real-world footage: target 15-20 cuts per minute (avg shot 3-4s)
- Gameplay footage: target 8-12 cuts per minute (avg shot 5-7s)
- Sprinkle in rapid cuts (<1s) for comedic emphasis or reaction beats

CONTENT:
- Cut dead air, filler words ("um", "uh", "like"), and long pauses ruthlessly
- Trim the start and end of each sentence tightly — no breathing room before the first word
- Prioritise funny, surprising, or high-energy moments
- The video must feel fast-paced and entertaining from the first second

STRUCTURE:
- Open with the strongest/funniest hook available — not "Hi guys welcome back"
- Build energy toward a climax or payoff
- End cleanly; don't let it drag after the last beat
"""

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.m4a'}


def _format_transcript(words: list[dict]) -> str:
    lines = []
    line_words = []
    line_start = None
    for w in words:
        if line_start is None:
            line_start = w['start']
        line_words.append(w['word'])
        if w['word'].endswith(('.', '?', '!', ',')) or len(line_words) >= 12:
            lines.append(f"[{line_start:.2f}s] {' '.join(line_words)}")
            line_words = []
            line_start = None
    if line_words:
        lines.append(f"[{line_start:.2f}s] {' '.join(line_words)}")
    return '\n'.join(lines)


def _format_shots(shots: list[dict]) -> str:
    return '\n'.join(
        f"  Shot {i+1}: {s['start']:.2f}s - {s['end']:.2f}s ({s['duration']:.2f}s)"
        for i, s in enumerate(shots)
    )


def _list_music(music_dir: Path) -> list[str]:
    if not music_dir.exists():
        return []
    return [p.name for p in sorted(music_dir.iterdir()) if p.suffix.lower() in AUDIO_EXTENSIONS]


def _extract_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Claude response")
    return json.loads(match.group())


def extract_captions(transcript: list[dict], source_in: float, source_out: float) -> list[dict]:
    """Return transcript words within [source_in, source_out] with timestamps relative to source_in."""
    return [
        {
            'word': w['word'],
            'start': round(w['start'] - source_in, 3),
            'end': round(w['end'] - source_in, 3),
        }
        for w in transcript
        if w['start'] >= source_in and w['end'] <= source_out
    ]


def build_plan(analysis: dict, music_dir: Path, client: anthropic.Anthropic) -> dict:
    clip = analysis['clips'][0]
    music_tracks = _list_music(music_dir)

    music_section = (
        f"AVAILABLE MUSIC TRACKS:\n" + '\n'.join(f"  - {t}" for t in music_tracks)
        if music_tracks else "AVAILABLE MUSIC TRACKS: none — set music to null"
    )

    prompt = f"""{STYLE_PROFILE}

RAW CLIP:
  File: {clip['path']}
  Duration: {clip['duration']:.1f}s ({clip['duration']/60:.1f} min)
  Resolution: {clip['width']}x{clip['height']} @ {clip['fps']:.0f}fps

SHOT BOUNDARIES (ffmpeg scene changes):
{_format_shots(clip['shots'])}

TRANSCRIPT (word-level timestamps):
{_format_transcript(clip['transcript'])}

{music_section}

TASK:
Produce an edit plan that cuts this raw footage into an engaging YouTube video in the ruder_dk style.
Return ONLY a JSON object — no explanation, no markdown fences — with this exact structure:

{{
  "estimated_duration": <total seconds of final edit as a number>,
  "music": <filename string from the music list, or null>,
  "segments": [
    {{
      "id": 1,
      "source_in": <start time in source clip, seconds>,
      "source_out": <end time in source clip, seconds>,
      "note": "<one-line description of what this segment contains>"
    }}
  ]
}}

Constraints:
- Use shot boundaries as natural cut points where possible
- Each segment should be 2-10s unless there is a specific reason to hold longer
- Start with the strongest hook available
- Total edit should be 50-80% of source duration
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    plan = _extract_json(raw)

    # Attach captions to each segment from the transcript
    for seg in plan['segments']:
        seg['captions'] = extract_captions(
            clip['transcript'], seg['source_in'], seg['source_out']
        )
        seg['duration'] = round(seg['source_out'] - seg['source_in'], 3)

    plan['source_clip'] = clip['path']
    return plan
