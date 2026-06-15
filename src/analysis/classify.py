import base64
import subprocess
from pathlib import Path

import anthropic

CONTENT_TYPES = ('facecam', 'gameplay', 'realworld', 'broll')


def _extract_frame(clip_path: Path, timestamp: float) -> bytes:
    result = subprocess.run(
        [
            'ffmpeg', '-ss', str(timestamp), '-i', str(clip_path),
            '-vframes', '1', '-f', 'image2', '-vcodec', 'png', 'pipe:1',
        ],
        capture_output=True, check=True,
    )
    return result.stdout


def classify_shot(clip_path: Path, timestamp: float, client: anthropic.Anthropic) -> str:
    """Return the content-type label for the frame at timestamp."""
    frame = _extract_frame(clip_path, timestamp)
    b64 = base64.standard_b64encode(frame).decode()

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b64},
                },
                {
                    "type": "text",
                    "text": (
                        f"Classify this video frame as exactly one of: {', '.join(CONTENT_TYPES)}.\n"
                        "facecam = person talking to camera; gameplay = screen/game footage; "
                        "realworld = real-world footage (not a screen); broll = anything else.\n"
                        "Reply with just the label."
                    ),
                },
            ],
        }],
    )
    label = msg.content[0].text.strip().lower()
    return label if label in CONTENT_TYPES else 'broll'
