# Changelog

All notable changes to H3 Continuity Studio are recorded here. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Replacement bridges (experimental).** A bridge can now *replace around the cut*: H3 regenerates a reviewed region of the two clips with exactly as many frames, so the full video keeps its length and recordings stay in sync. You confirm the exact region, render candidates, compare them in context with the original cut, and select one; nothing plays until you do, and a stale, failed or missing candidate plays the original footage. Joins are not yet validated with real generations. See [Joins and bridges](guide/continuity/joins-and-bridges.md#replacement-bridges).
- **Dialogue cues.** A recording's exact words at its own times, with speaker, on-screen or voiceover portrayal and a check against the recording. Import them from a timed transcript, take them from the Story or type them. Clips speak the cues in their window as `<d>` lines, and replacements keep on-screen speech and footage you mark. See [Dialogue cues](guide/sound/dialogue.md).
- **Locked recordings.** An uploaded audio clip can be locked to the sequence clock: bridges inside it replace footage instead of adding time, and the Timeline names any inserted bridge or setting that would move the picture off it.

### Changed

- Timelines that use replacements, cues or locks list them in `requires`. From this version on, a reader that doesn't know a listed feature stops with *this Timeline needs a newer H3 Continuity* instead of misreading the file. Existing bridges keep their meaning: a bridge without `mode` still inserts time.

## [0.2.0] - 2026-11-03

### Fixed

- **Saved stories keep their frame guides.** Loading a saved story into a workflow whose generator settings differ (for example a seed set to randomize after each run) no longer discards accepted frame guides. The scene anchors pinned to those guides are kept too. Still candidates, in-flight still jobs and links to saved takes are still skipped, because they belong to the old generator and sequence.
- **Uploading a guide no longer marks a saved story as rewired.** The Timeline's uploaded-guide and uploaded-asset lists are no longer compared as generator wiring, so a guide upload alone doesn't make a later load skip the saved renders.

## [0.1.0] - 2026-11-02

Initial public release, with the memory demo.

- **H3 Timeline:** frame, token and audio timing, segment encoding, full-movie assembly, exact-length boxes and windowed long boxes.
- **H3 Story:** an OpenAI-compatible writer (local or cloud) that plans and writes boxes from an idea, with revisions and Undo.
- **Story bible and continuity:** entities, looks, cast linking, pinned cast moments and scene anchors keep characters and places consistent across scenes and camera angles.
- **Studio:** one editing surface for Story, Timeline, pictures, references, takes and audio.
- **Frame images:** still prompts, candidate generation, guide acceptance and uploaded guides.
- **References, timed text and audio:** reference replacement and preparation, RefMods, Whisper timing, timed text and voice references.
- **Saved Story library** and the headless **Timeline API**.

[0.2.0]: https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/releases/tag/v0.2.0
[0.1.0]: https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/releases/tag/v0.1.0
