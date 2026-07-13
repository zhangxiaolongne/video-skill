# Current Development Batch

## Batch Header

- Batch ID: `V3-07`
- Name: Personal/Subject Memory
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V3-07`
- Prerequisite: published `V3-06 Publishability Tiers`
- Publication: published as one complete version after `283 passed` and all project checks

## Goal Delta

V3-07 turns explicit project requirements and prior user revisions into reusable,
auditable creative context. It supports project memory and explicitly identified
subject memory while preserving provenance, fulfillment state, conflicts, and
non-application boundaries.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `identity_scope` | Separate project and subject memory | Project identity comes from config; subject identity requires explicit id and display name and is never guessed. | `completed` |
| `alias_binding` | Keep identity lookup auditable | Explicit aliases are normalized and deduplicated without inferring new names. | `completed` |
| `explicit_preferences` | Retain user creative choices | Style, BGM, text, cover, rhythm, transition, composition, duration, audio, ending, shot, and custom preferences accept explicit categorized statements. | `completed` |
| `hard_constraints` | Preserve prohibitions | Required and forbidden instructions remain hard entries that future candidate review must respect. | `completed` |
| `revision_history` | Remember complete user feedback | Full revision request text and every recognized semantic clause remain separate provenance-bound entries. | `completed` |
| `fulfillment_truth` | Distinguish request from success | Applied, partial, manual-only, not-selected, blocked, and unverified outcomes remain visible; requests are never promoted to confirmed success. | `completed` |
| `selected_style_only` | Avoid fake style memory | Unselected template/style/technique/arc vocabulary is excluded; only an explicit selected id may become observed memory. | `completed` |
| `cross_project_import` | Persist and reuse memory locally | Same-identity reruns preserve prior explicit entries while refreshing config facts; imports require exact scope/id match, and project-only entries cannot leak into subject reuse. | `completed` |
| `conflict_preservation` | Prevent silent overwrite | Duplicate identical entries merge provenance; opposing instructions remain an unresolved conflict requiring user resolution. | `completed` |
| `advisory_retrieval` | Make memory useful without hidden edits | Retrieval context is generated for later host-Agent/editor use, but memory is never automatically applied to style, BGM, shots, timeline, or media. | `completed` |

## Guardrails

- Generic `artist_name`, filenames, source labels, and template compatibility do
  not establish a subject identity or preference.
- Project revisions enter project memory by default; moving them into subject
  memory requires an explicit flag and keeps them unverified for reuse.
- Changing the canonical memory identity is blocked unless the operator supplies
  `--replace-existing`; silent identity replacement is forbidden.
- A selected style is observed history, not proof that the user liked the result.
- Publishability evidence is bound for audit but does not become preference.
- CLI does not apply memory, select style/BGM/shots, mutate timelines, render,
  call models, or access the network.
- Model, Schema, CLI wiring, tests, docs, and incidental fixes are support work,
  not separate V3-07 tasks.

## Real Acceptance

- `runs/interview_contrast` is correctly treated as project memory because its
  configured artist identity is generic and does not prove a single subject.
- The canonical memory contains 13 entries: 8 confirmed project facts and 5
  requested revision memories.
- The complete user request is preserved alongside `呼吸感`, `更克制`,
  `减少字幕`, and `不要压人声`; all four parsed requests remain
  `manual_only`, not confirmed success.
- `allow_music: false` becomes a hard project BGM prohibition.
- Unselected style vocabulary and the publishability verdict do not become
  preferences. No absolute local path appears in the canonical memory.

## Next Work

V3-07 is closed after full project checks and one-version publication. V3-08 V3
Release remains inactive until its complete release-audit batch is planned.
