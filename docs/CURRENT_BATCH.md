# Current Development Batch

## Batch Header

- Batch ID: `V2-01`
- Name: Real Video Aesthetic Baseline
- Type: real-video aesthetic editing capability stage
- Status: `planned`
- Capability gate: `V2-01`
- Started: `2026-07-04`
- Commit/push policy: do not commit, tag, or push until the V2-01 capability
  and its validation evidence close as one coherent version

## Stage Outcome

Before this stage, `v0.29.0` can run a complete engineering pipeline and can
promote revised timelines, but the real-video trial still shows weak editing
judgment: fixed-window bias, shallow content understanding, raw source-layout
retention in the final frame, incomplete BGM rhythm judgment, and no mature
second-pass aesthetic rewrite.

After this stage, the Skill should treat at least one real project, with
`runs/chenhaoyu_klein_blue` and the source video
`陈昊宇乘风之夜助力秀《克莱因蓝的独白》.mp4` as the primary benchmark, as an
aesthetic editing case rather than only a media pipeline case. V2-01 must
generate a real-video aesthetic baseline that recommends duration, identifies
highlights and weak areas, proposes multiple edit concepts, audits final-frame
composition and safe reframe candidates, binds BGM/text/rhythm risks, reviews
the first cut, and prepares a second-cut candidate plan.

This stage does not need to produce a perfect final video. It must prove that
the system can explain and improve an edit using real-video evidence. That is
the bridge from "engineering-valid MP4" to "editable creative draft."

## Countability Audit Before Implementation

Audit status: `passed`. V2-01 is a capability stage, not a field/schema/test
cleanup. Supporting schemas, tests, fixtures, bug fixes, and refactors do not
count as independent tasks unless they directly deliver one of the outcomes
below.

| ID | Countable stage outcome | Why it counts | Status |
|---|---|---|---|
| `V201-01` | Real-video benchmark binding | Selects and records the primary real video, project path, source evidence, target use case, and known current-output weaknesses. | `planned` |
| `V201-02` | Aesthetic target profile | Defines the desired cut type, platform, target emotion, pacing, subtitle density, BGM role, and acceptable manual intervention level. | `planned` |
| `V201-03` | Duration recommendation from evidence | Recommends short, standard, and extended durations from actual source density, highlight distribution, BGM constraints, and platform assumptions. | `planned` |
| `V201-04` | Real highlight and weak-area map | Scores candidate ranges for hook, emotional value, visual usefulness, speech/audio clarity, rhythm, ending strength, and risk. | `planned` |
| `V201-05` | Multi-concept edit planning | Produces at least three named edit concepts, such as emotional portrait, stage-energy cut, and narrative context cut, with keep/drop rationale. | `planned` |
| `V201-06` | Hook/build/payoff refinement | Converts the selected concept into a refined structure with opening, escalation, breath, payoff, and ending intent. | `planned` |
| `V201-07` | BGM and source-audio aesthetic fit | Reviews direct BGM, video-extracted audio, embedded source audio, and no-BGM modes for mood fit, ducking pressure, contamination, and rhythm risk. | `planned` |
| `V201-08` | Text and subtitle timing plan | Plans title/subtitle/emphasis timing with readability, density, performance-occlusion, and rhythm-pressure checks. | `planned` |
| `V201-09` | Transition and pacing plan | Defines where cuts should be clean, held, dissolved, paused, or left as manual review points based on content and audio evidence. | `planned` |
| `V201-10` | First-cut aesthetic self-review | Reviews the current preview/final or timeline candidate for weak opening, dead zones, emotional breaks, BGM conflicts, subtitle overload, and ending weakness. | `planned` |
| `V201-11` | Second-cut candidate plan | Converts the self-review into a concrete second-cut candidate with proposed segment replacements, duration changes, BGM/text implications, and expected improvement. | `planned` |
| `V201-12` | Real-video acceptance report | Summarizes whether the real-video baseline is usable, which concept is strongest, what remains manual, and what V2-02 must solve. | `planned` |
| `V201-13` | Final-frame composition and reframe audit | Identifies persistent source layout, subject occupancy, unsafe crop risks, and manual-safe crop/reframe candidates without claiming an edit was rendered. | `planned` |

## JSON Governance

- V2-01 may add one Tier 1 canonical machine artifact for the real-video
  aesthetic baseline plus one human Markdown report.
- Separate JSON is allowed only for external candidate quarantine/import,
  generated schema boundaries, media validation, run audit, or release-critical
  evidence chains.
- Ordinary concept summaries, status, warnings, next actions, self-review, and
  second-cut guidance should be folded into the canonical baseline artifact or
  Markdown report.
- `runs/` and generated local evidence remain visible through filesystem and
  `status` storage reports. They may be Git-ignored only as an explicit capacity
  boundary, never for cosmetic cleanliness; source/final evidence remains local
  until an explicit deletion decision.

## Supporting Re-Architecture

The V2-01 capability is supported by a non-counting repository cleanup:
consolidate behavior validation in pytest, reduce duplicate full-pipeline
checks, split high-coupling orchestration, and converge redundant JSON chains.
This work must not change the thirteen V2-01 outcomes, claim a new editing
capability, delete selected source/final evidence or cache automatically, or
rewrite Git history without an explicit later approval.

Current implementation: run-cache cleanup, visible storage accounting, compact
validation orchestration, distribution exclusion, Git local-artifact boundary,
integration tests split by business domain, and the first workspace module split
(state, records, proposal I/O, and read-only summaries) are complete. Cache
cleanup is explicit maintenance only and must never run implicitly. High-coupling
proposal execution and workflow business orchestration have been converged:
proposal keeps context, host-Agent handoff, candidate quarantine, validation,
and atomic promotion; workflow keeps a current plan and external execution
review. Acceptance now exposes next commands from one report instead of a
repair/approval/dry-run/execution chain. FCPXML keeps draft, import review, and
manual repair planning, while its simulated approval/dry-run/execution chain is
removed. BGM recommendation keeps context, candidate quarantine, validated
recommendations, explicit selection, and fit review; its duplicate request JSON
is folded into the host-Agent handoff. Workspace status/doctor logic is now an
independent module and feature modules import state/record/error primitives
directly. Git history compaction remains separately pending explicit force-push
approval.

## Acceptance Criteria

- V2-01 must bind to a real project and identify the source video, existing
  preview/final artifacts when present, and the current known edit-quality gaps.
- The baseline must recommend at least three durations and explain tradeoffs
  with evidence, not fixed defaults.
- The highlight map must score at least hook, emotion, visual usability, audio
  clarity, rhythm, information density, ending strength, and risk.
- The baseline must inspect the actual final frame for persistent source layout,
  subject occupancy, branding/letterbox intrusion, safe crop constraints, and
  whether the exported portrait frame is visually usable. A crop/reframe
  recommendation is planning, not proof that media was re-rendered.
- The system must propose at least three edit concepts with different creative
  intent and keep/drop rationale.
- BGM analysis must cover direct uploads, extracted video audio, source embedded
  audio, multiple candidates, and no-file-yet planning. Extracted video mixes
  must remain marked as mixed/contaminated unless separation evidence exists.
- Text/subtitle planning must include density, readability, timing, and whether
  text would occlude performance or fight BGM/rhythm.
- Self-review must identify concrete first-cut weaknesses and cite available
  timeline/media/evidence refs.
- The second-cut candidate plan must name specific changes and downstream
  consequences; it must not claim rendered media has already changed unless a
  render actually happened.
- V2-01 may use host-Agent judgment, local models, search, image2, or third
  party/local tools only through explicit, visible, non-paid, provenance-recorded
  boundaries. Paid APIs, hidden provider calls, hidden network calls, and
  fabricated content understanding remain forbidden.
- V2-01 planning and implementation must not count isolated fields, schemas,
  tests, refactors, or bug fixes as version tasks.

## Closeout

- Final status: `planned`
- Required validation before completion:
  - focused V2-01 real-video baseline tests
  - current batch/governance contract tests
  - JSON/schema validation for any new canonical artifact
  - real-project smoke run on the primary benchmark
  - `run_checks.py --skip-pytest` or a documented narrower equivalent if the
    implementation remains documentation-only
  - explicit publication decision after the V2-01 capability is complete
- Final-goal delta target: move from a published engineering pipeline to a
  real-video aesthetic baseline that can explain why one cut is stronger than
  another and how to improve it.
