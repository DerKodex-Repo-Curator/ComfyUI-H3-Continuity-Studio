# Mobile saved-video playback implementation plan

**Spec:** ../specs/2026-11-05-mobile-saved-video-design.md
**Goal:** Show existing rendered media on Android and thumbnails for older saved takes.

- [x] Add red media tests: real HDR High10 source produces bounded 8-bit SDR Main/AAC preview, source unchanged, cache reuse/invalidation, output path traversal rejected. Add status regression for older thumbnails without false done state, including reordered boxes.
- [x] Implement a small `h3_continuity/video_preview.py` cache/encoding helper and `/h3c/video/preview` GET route; retain existing file/download responses and originals.
- [x] Add red JS player tests for phone URLs, API prefixes, desktop decode fallback, inline playback/poster and stable refresh; implement shared URL helper and Studio wiring/cache revisions.
- [x] Run full CPU suite, exact saved-workflow checks and live browser playback over HTTPS. Obtain one independent read-only review; fix substantive findings with regressions.
- [ ] Deliver follow-up PR/tagged release, fast-forward both main checkouts and restart ComfyUI. Verify served code, actual compatible video metadata, old thumbnails and unchanged originals. Record exact phone-test limits.

Independent review found Windows original-file locking and cached requests waiting behind unrelated encoders. Both reproduced in failing regressions, then fixed by taking a coordinated private source snapshot and bypassing the encoder lock for cache hits. Full suite: 143 JS +260 Python, zero skips; actual HTTP range returns206, path traversal400; actual source converts to Main8/SDR/AAC unchanged. No deferred findings. Direct Android device and perceptual HDR acceptance remain unverified.
