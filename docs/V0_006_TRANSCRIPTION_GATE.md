# V0-006 Transcription Gate

V0-006 opens a local transcription gate for source media. It creates the
canonical transcript ledger when local faster-whisper can run without network
downloads, and it records explicit skipped or dependency-failure states when it
cannot.

## Scope

- `features.transcription: off` marks `transcribe` as `skipped` and does not
  create fake transcript data.
- `features.transcription: auto` uses local faster-whisper when available and
  skips with a warning when faster-whisper or a local model is unavailable.
- `features.transcription: required` fails with exit code `4` when
  faster-whisper is unavailable or local model loading/transcription fails.
- Successful runs write `.artist-portrait/data/transcripts.jsonl`.
- `status`, `doctor`, run metadata, and artifact summaries expose transcript
  count, invalid ledgers, missing required dependency, and invalidated
  transcription state.
- A changed source ledger invalidates completed transcription output.

## Boundaries

faster-whisper is treated as a local ASR evidence tool. Its output can support
audible-text evidence, but it does not classify whether text is interview,
lyrics, role dialogue, captions, or voice-over.

Still closed:

- OpenCV or visual analysis
- embeddings
- text understanding beyond raw ASR records
- BGM selection, beat analysis, or music/timeline fitting
- creative proposals
- timeline generation
- preview rendering
- remote model calls
- model downloads
- network search
- image generation or image editing

## Data Contract

`TranscriptRecord` is the canonical transcription unit. It stores:

- source identity and fingerprint
- segment index and source time range
- text and optional word timestamps
- language, speaker, and text type fields
- method, method version, confidence, evidence, confirmation state, and risk
  flags

`text_type` remains `null` unless a later gate or user confirmation classifies
the transcript.

## Validation Expectations

- Tests must not require faster-whisper or local Whisper models to be installed.
- faster-whisper availability and output are simulated in tests.
- `transcription: required` must fail before writing fake transcripts when the
  dependency or local model is unavailable.
- Local-only model loading must be preserved in the adapter.
