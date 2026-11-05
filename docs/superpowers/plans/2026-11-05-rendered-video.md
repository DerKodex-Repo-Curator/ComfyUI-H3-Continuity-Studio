# Rendered video playback implementation plan

> Execute inline using the existing Python/PyAV and plain DOM JavaScript stack.

**Goal:** Play current rendered clips together before completion and choose audio muxing.
**Spec:** ../specs/2026-11-05-rendered-video-design.md

## Constraints and review focus

Preserve source-filled previews, complete/API exports and original segment files.
Handle noncontiguous rendered boxes, stale clips, missing media, correct soundtrack
offsets after gaps, cache invalidation, H3/uploaded soundtrack switching, and download consistency.
No inference, deployment, release or new dependency is needed.

## Tasks

- [x] Add failing Python media/status tests and JS persistence/player tests.
- [x] Extend partial_video.build for compact rendered clips and optional muxing.
- [x] Carry persisted mux_audio through Timeline parsing/model and complete assembly
  fingerprints; status supplies the correct export for the setting.
- [x] Add the checkbox using existing Viewer controls; label compact partials;
  keep partial links usable during render queues.
- [x] Run targeted tests, full CPU suite, syntax/diff checks, and UI verification.
- [x] Update the user guide and recovery ledger with verified results.

Verified 2026-11-05: 123 JS + 248 Python tests; actual Studio desktop/mobile control smoke; strict guide build; syntax and diff checks. Independent review findings fixed with regressions. No live deployment or GPU rendering.
