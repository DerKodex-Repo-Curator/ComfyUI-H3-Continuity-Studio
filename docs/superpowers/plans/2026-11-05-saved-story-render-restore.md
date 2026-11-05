# Saved story render restoration implementation plan

**Goal:** Preserve render folders when reopening stories across equivalent sessions.
**Spec:** ../specs/2026-11-05-saved-story-render-restore-design.md
**Architecture:** Normalize UI-only serialization in the existing shared comparator; preserve actual generator checks. Plain JavaScript, no dependencies.

- [x] Add `tests/js/story_render_restore.test.mjs`: saved sequence/candidate preservation for image-output selection, empty widget collections and output display widgets; incompatible model/input/link/setting changes must fork; legacy unlabelled widget values must remain significant; nested subgraphs covered.
- [x] Run the new file and confirm harmless-session regressions fail before implementation.
- [x] Fix `web/h3c_story_library.mjs`, update all browser cache revisions for its import and verify against the real v17/newer snapshots.
- [x] Run full CPU suite, syntax/diff and strict documentation checks; obtain one independent code review and address substantive findings with regressions.
- [ ] Prepare v0.12.7 changelog/release notes, commit only task files, create/link PR and merge after checks.
- [ ] Publish annotated tag/release, fast-forward development and custom-node main, verify preservation and matching files. Restart existing ComfyUI with its original command and verify HTTP/media health.

Review focus: actual input changes stay significant; auxiliary seed controls are not shifted; legacy widget lists are preserved; subgraph generators obey the same rules; no media/autosave mutation during verification. Execute inline; no additional approval needed for the authorized delivery sequence.

Verification: six initial red regressions passed after normalization. Independent review found overly broad trimming of CustomCombo/seed controls; two new regressions failed, then passed after limiting the display exception to OrreryRefinementResult.comparison. Final suite: 140 JS + 254 Python, zero skips. Actual saved-session restoration, CustomCombo option swap and seed-control changes verified. No deferred review findings.
