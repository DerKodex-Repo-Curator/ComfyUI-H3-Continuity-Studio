# Saved playback clock implementation plan

Spec: ../specs/2026-11-05-saved-playback-clock-design.md

- [x] Reproduce older-take omission and48fps picture truncation in red regressions.
- [x] Match saved footage by box ID; distinguish saved playback from current rendering.
- [x] Convert native video windows to delivered fps and invalidate assembly caches.
- [x] Preserve authored uploaded-track positions across saved-length changes.
- [x] Allow older native memory; retain identity/resolution/file/selected-time checks.
- [x] Run full suite, strict docs and actual sequence dry-run; fix review findings.
- [ ] PR/merge/release/deploy/restart and rebuild real playback with original assets preserved.
