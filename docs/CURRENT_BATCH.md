# Current Development Batch

## Batch Header

- Batch ID: `V3-05`
- Name: NLE Round-Trip Plus
- Type: product capability milestone
- Status: `completed`
- Capability gate: `V3-05`
- Prerequisite: published `V3-04 A/B Version Review`
- Publication: one commit/push only after complete validation

## Goal Delta

V3-05 turns the existing editor package and planning-only interchange maps into
a practical local NLE handoff: source-bound FCPXML, EDL, Resolve/Premiere marker
sidecars, cue sheet, relink manifest, version identity, and an explicit external
import/relink/playback/round-trip acceptance checklist.

## Internal Acceptance Checklist

| ID | Outcome | Acceptance | Status |
|---|---|---|---|
| `source_relink_manifest` | Make source identity actionable | Every used source binds location, expected/actual hash, file URI, timeline items, and relink status. | `completed` |
| `source_freshness` | Prevent silent substitution | Missing or hash-mismatched media blocks direct-link FCPXML instead of claiming success. | `completed` |
| `version_identity` | Preserve compared-version context | Package identifies canonical timeline and binds current A/B review when available. | `completed` |
| `editable_fcpxml` | Deliver an editable FCP timeline | Write structurally valid FCPXML with direct source URIs, timeline ranges, and markers. | `completed` |
| `edl_handoff` | Support broad NLE interchange | Write a picture edit decision list with source/record timecodes and clip names. | `completed` |
| `resolve_markers` | Carry review intent into Resolve | Write Resolve marker CSV with manual and A/B findings. | `completed` |
| `premiere_markers` | Carry review intent into Premiere | Write Premiere marker CSV without pretending it is a native project. | `completed` |
| `unified_cue_sheet` | Keep clip/audio intent readable | Write clip ranges, source ranges, audio guidance, and creative intent in one cue sheet. | `completed` |
| `editor_markers` | Enable continued refinement | Manual priorities and A/B goal findings become inspectable timeline markers. | `completed` |
| `external_acceptance` | Define real round-trip proof | Eight pending checks cover pre-import, import, relink, timeline, markers, audio, playback, and re-export. | `completed` |

## Guardrails

- Written files are NLE candidates, not proof of successful import or playback.
- Direct URI requires both file existence and exact source-ledger hash.
- Missing media blocks direct FCPXML linking but does not hide usable sidecars.
- Audio automation remains cue guidance unless the target format truly carries it.
- CLI does not open an NLE, relink, render, mutate timelines, select music, call models, or access the network.

## Real Acceptance

- `runs/interview_contrast`: one real source hash matches; six deliverables written; 6 timeline clips, 7 markers, 6 cues; import/relink/playback remain pending.
- Generated integration fixture: absent fake source produces visible missing/relink state and blocked FCPXML direct-link status while sidecars remain inspectable.
- Stage/event projects are not promoted to current round-trip proof when their current editor-package prerequisites are absent or stale.

## Next Work

V3-06 Publishability Tiers may begin only after V3-05 passes full project checks
and is published as one complete capability version.
