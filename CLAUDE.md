# AI Video Editor — ruder_dk style

## What this is
A personal AI video editing pipeline that takes raw footage, analyzes it, and produces a DaVinci Resolve-ready FCPXML timeline + SRT caption file in the editing style of ruder_dk.

## Stack
- Python 3.13, venv at `.venv/`
- `faster-whisper` for local transcription
- `ffmpeg` for shot detection and metadata
- `anthropic` SDK (claude-sonnet-4-6) for edit planning
- `claude-haiku-4-5-20251001` for shot classification
- Output: FCPXML + SRT (open in DaVinci Resolve free)

## Running the pipeline

### Activate venv first
```
.\.venv\Scripts\activate
```

### Stage 2 — Analyze raw footage
```
python -m src.main analyze rawfootage --no-classify
```
Output: `output/analysis.json`

### Stage 3 — Plan the edit (requires ANTHROPIC_API_KEY)
```
python -m src.main plan
```
Output: `output/edit_plan.json` — review and edit this before proceeding

### Stage 4 — Assemble (NOT YET BUILT)
```
python -m src.main assemble
```
Output: `output/timeline.fcpxml` + `output/captions.srt`

## Architecture
```
rawfootage/  →  analyze  →  output/analysis.json
                                    ↓
                              plan (Claude)
                                    ↓
                         output/edit_plan.json  ← YOU REVIEW HERE
                                    ↓
                             assemble (TODO)
                                    ↓
                   output/timeline.fcpxml + output/captions.srt
                                    ↓
                            DaVinci Resolve
```

## Current status
- [x] Stage 1: Ingest (`src/ingest.py`)
- [x] Stage 2: Analysis (`src/analysis/` — shots, transcription, classification)
- [x] Stage 3: Edit planning (`src/planning/planner.py`)
- [ ] Stage 4: Assembly — FCPXML + SRT writer (`src/assembly/`) ← NEXT
- [ ] Stage 5: Review UI (nice-to-have later)

## Key files
- `src/main.py` — CLI entry point (`analyze`, `plan`, `assemble` commands)
- `src/planning/planner.py` — Claude prompt + edit plan logic
- `output/analysis.json` — latest analysis run (4-min Minecraft clip)
- `output/edit_plan.json` — latest Claude edit plan (once `plan` has been run)
- `assets/music/` — drop music tracks here for Claude to choose from

## Style profile (ruder_dk)
- Vlog footage: 15-20 cuts/min, avg shot 3-4s
- Gameplay: 8-12 cuts/min, avg shot 5-7s
- Word-by-word captions burned into video (bottom-center)
- Continuous music underlayer throughout
- Hooks in first 10-15 seconds

## Environment variables needed
- `ANTHROPIC_API_KEY` — set via `setx ANTHROPIC_API_KEY "sk-..."` in a regular terminal
