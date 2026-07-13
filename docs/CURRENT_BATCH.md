# Current Development Batch

## Batch Header

- Batch ID: `V3-06`
- Name: Publishability Tiers
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V3-06`
- Prerequisite: published `V3-05 NLE Round-Trip Plus`
- Publication: `published` as one commit/push after complete validation

## Goal Delta

V3-06 turns scattered technical and aesthetic evidence into one honest,
per-version release decision. It classifies playable outputs and plan-only
candidates into four exclusive tiers, preserves every blocker and evidence gap,
and gives concrete next actions without choosing a version for the user.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `exclusive_quality_tiers` | Produce one unambiguous verdict | Every reviewed version is exactly `publishable`, `previewable`, `manual_refinement_required`, or `unusable`. | `completed` |
| `media_existence_truth` | Reject missing outputs | A render record without current media, or with a changed hash, is unusable. | `completed` |
| `technical_validity_boundary` | Preserve delivery truth | Technical validity is required for playback but never sufficient for publishing. | `completed` |
| `first_cut_aesthetic_binding` | Carry the nine-domain first-cut judgment | Canonical output binds opening, pacing, emotion, BGM/voice, text, ending, transitions, composition, and delivery review. | `completed` |
| `second_cut_comparison_binding` | Carry rendered A/B evidence | Second cut binds all nine comparison domains and its explicit publishability verdict. | `completed` |
| `sound_and_bgm_gate` | Keep sound coupled to editing | Source audio, added BGM, voice pressure, and unresolved music decisions remain visible blockers or refinements. | `completed` |
| `text_and_composition_gate` | Prevent plan-only aesthetic promotion | Missing transcript/text render, candidate-specific framing, and transition/ending gaps cannot be hidden by technical QC. | `completed` |
| `editable_delivery_boundary` | Separate MP4 use from NLE delivery | NLE relink/round-trip gaps apply only to the canonical editable-delivery boundary and do not invalidate unrelated rendered media. | `completed` |
| `actionable_recovery` | Make every deficit repairable | Every issue carries domain, severity, disposition, evidence, and a concrete next action. | `completed` |
| `no_automatic_selection` | Preserve user authorship | The report may expose the highest available tier and tied candidates, but selected version and automatic winner remain null. | `completed` |

## Tier Semantics

- `publishable`: current playable media has technical validity, explicit
  aesthetic approval, and no known publish blocker, refinement, or evidence gap.
- `previewable`: current playable media has no known publish blocker, but still
  has bounded refinement work or evidence gaps.
- `manual_refinement_required`: current playable media has at least one explicit
  publish blocker that requires human/editorial work.
- `unusable`: media is absent/stale, technical validity failed, or the candidate
  is still plan-only.

## Guardrails

- A valid MP4, rhythm pass, schema pass, or delivery acceptance cannot produce
  `publishable` without aesthetic evidence.
- A plan-only revision can never become previewable merely because its proxy
  scores are high.
- The CLI does not select a version, mutate timelines, render media, choose BGM,
  call models, access the network, or claim human playback occurred.
- Fields, schema, tests, documentation, and incidental fixes are support work,
  not separate V3-06 tasks.

## Real Acceptance

- `runs/interview_contrast` contains three reviewed versions.
- Canonical final: media present and technically valid, but first-cut review is
  `not_publishable`; tier is `manual_refinement_required`.
- Rendered 60-second second cut: media/hash current and technically valid, but
  semantic continuity, text, composition, fine pacing, and full aesthetic
  approval remain unresolved; tier is `manual_refinement_required`.
- Controlled revision application: plan-only with no playable media; tier is
  `unusable`.
- No version is called publishable and no version is selected automatically.

## Next Work

V3-07 Personal/Subject Memory may begin only after V3-06 passes full project
checks and is published as one complete capability version.
