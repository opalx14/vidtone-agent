# VidTone Agent Project Plan

## Goal

Build a runnable hackathon MVP for Track 2: Video Captioning.

The app should convert short videos into four caption styles:

1. Formal
2. Sarcastic
3. Humorous-tech
4. Humorous-non-tech

## MVP scope

- Streamlit upload UI
- Video preview
- Metadata extraction
- Keyframe extraction
- Caption generation in mock mode
- Fireworks API client for real mode
- Judge Agent scoring
- JSON/CSV export
- Docker support

## Differentiator

Self-Judging Caption Agent:

```text
CaptionAgent generates -> JudgeAgent scores -> weak captions are revised
```

This gives the project a stronger story than a one-shot caption generator.

## Build phases

### Phase 1: Runnable skeleton

Status: done

- apps/streamlit/main.py
- config
- pipeline
- mock captions
- export

### Phase 2: Video processing

Status: basic version done

- metadata extraction
- duration warning
- keyframe extraction

### Phase 3: Real model integration

Status: client scaffold done

Next:

- confirm hackathon model names
- set `FIREWORKS_MODEL`
- test real output parsing

### Phase 4: Improve video understanding

Next:

- add audio transcription
- add frame description model
- merge transcript + visual notes into stronger video context

### Phase 5: Submission polish

Next:

- record demo video
- write pitch slides
- push public GitHub
- deploy Streamlit app or provide Docker run instructions
