from pathlib import Path
from faster_whisper import WhisperModel

_model: WhisperModel | None = None


def _get_model(size: str) -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model


def transcribe(clip_path: Path, model_size: str = "base") -> list[dict]:
    """Return word-level transcript: [{"word", "start", "end"}, ...]"""
    model = _get_model(model_size)
    segments, _ = model.transcribe(str(clip_path), word_timestamps=True)
    words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                words.append({
                    'word': w.word.strip(),
                    'start': round(w.start, 3),
                    'end': round(w.end, 3),
                })
    return words
