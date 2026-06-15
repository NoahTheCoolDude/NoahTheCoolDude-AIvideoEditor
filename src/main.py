import json
import os
from pathlib import Path

import click

from src.ingest import find_clips, probe
from src.analysis.shots import detect_shots, cuts_to_segments
from src.analysis.transcribe import transcribe
from src.analysis.classify import classify_shot


@click.group()
def cli():
    pass


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), default='output',
              show_default=True, help='Directory to write analysis JSON')
@click.option('--whisper-model', default='base', show_default=True,
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              help='Whisper model size (larger = more accurate, slower)')
@click.option('--classify/--no-classify', default=True, show_default=True,
              help='Run Claude Vision content classification (requires ANTHROPIC_API_KEY)')
@click.option('--threshold', default=0.35, show_default=True,
              help='Scene-change detection sensitivity (0–1, lower = more cuts detected)')
def analyze(input_dir, output, whisper_model, classify, threshold):
    """Analyze all clips in INPUT_DIR and write a review JSON to OUTPUT."""
    output.mkdir(parents=True, exist_ok=True)

    clips = find_clips(input_dir)
    click.echo(f"Found {len(clips)} clip(s) in {input_dir}")

    anthropic_client = None
    if classify:
        try:
            import anthropic
            anthropic_client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        except KeyError:
            click.echo("Warning: ANTHROPIC_API_KEY not set — skipping classification.", err=True)
            anthropic_client = None

    results = []

    for clip_path in clips:
        click.echo(f"\n→ {clip_path.name}")

        click.echo("  [1/3] Probing metadata...")
        meta = probe(clip_path)

        click.echo("  [2/3] Detecting shots...")
        cuts = detect_shots(clip_path, threshold=threshold)
        segments = cuts_to_segments(cuts, meta['duration'])
        click.echo(f"        {len(segments)} shots detected")

        if anthropic_client:
            click.echo("  Classifying shots...")
            for seg in segments:
                midpoint = (seg['start'] + seg['end']) / 2
                seg['content_type'] = classify_shot(clip_path, midpoint, anthropic_client)
            counts = {}
            for seg in segments:
                counts[seg['content_type']] = counts.get(seg['content_type'], 0) + 1
            click.echo(f"        {counts}")

        click.echo(f"  [3/3] Transcribing with Whisper ({whisper_model})...")
        words = transcribe(clip_path, model_size=whisper_model)
        click.echo(f"        {len(words)} words transcribed")

        results.append({**meta, 'shots': segments, 'transcript': words})

    out_file = output / 'analysis.json'
    out_file.write_text(json.dumps({'clips': results}, indent=2))
    click.echo(f"\nDone. Review file written to {out_file}")


if __name__ == '__main__':
    cli()
