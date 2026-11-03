# Changelog

All notable changes to H3 Continuity Studio are recorded here. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Replacement bridges (unavailable).** A Timeline can describe a bridge that *replaces around the cut*: H3 regenerates a reviewed region of the two clips with exactly as many frames, so the full video keeps its length and recordings stay in sync. In tests with real generations every candidate still jumped at its joins, so this version ships them switched off: nothing renders or plays a replacement, the original cut plays, and the Studio only offers to remove one. See [Joins and bridges](guide/continuity/joins-and-bridges.md#replacement-bridges).
- **Dialogue cues.** A recording's exact words at its own times, with speaker, on-screen or voiceover portrayal and a check against the recording. Import them from a timed transcript, take them from the Story or type them. Clips speak the cues in their window as `<d>` lines, and replacements keep on-screen speech and footage you mark. See [Dialogue cues](guide/sound/dialogue.md).
- **Locked recordings.** An uploaded audio clip can be locked to the sequence clock: no bridge may add time inside it, so its cuts stay cuts, and the Timeline names any inserted bridge or setting that would move the picture off it.
- **Agent skill pack.** `skills/` now holds seven skills that work together. `h3-continuity-video` is the entry, and six scoped skills cover joins and visual memory, timing, references and guides, sound and text, Story and Cast, and the API. Together they describe every feature, including visual memory, plates, RefMods, takes, the continuity check, long clips and voice clips, which the earlier single skill did not mention. `GET /h3c/timeline/instructions` serves the whole pack as `skills` (`instructions_revision` `external-instructions-v8`), and `python skills/install.py` links it into the agent skill folders on this computer.

### Changed

- **Visual memory at a cut with speech.** When someone speaks on either side of a cut, the clip after it remembers the five frames before the cut instead of the full preceding video. H3 copied that video's lip movement onto the new shot, so the new clip's lines went out of sync. Such clips need a render. See [Visual memory](guide/continuity/visual-memory.md#how-it-works).
- Timelines that use replacements, cues or locks list them in `requires`. From this version on, a reader that doesn't know a listed feature stops with *this Timeline needs a newer H3 Continuity* instead of misreading the file. Existing bridges keep their meaning: a bridge without `mode` still inserts time.

## [0.4.0] - 2026-11-03

### Added

- **Resizable Studio panes.** Drag the handles between References, the center and the Inspector, and above the Timeline (arrow keys work on a focused handle; double-click resets a pane). The original fixed sizes are the minimums. A taller Timeline pane shows more lanes without scrolling; rows keep their height.
- **Timeline zoom.** `−`, `+` and `Fit` in the Timeline toolbar, or Ctrl+scroll over the lane to zoom around the pointer, from 100% (fit) to 1600%.
- **Layout memory.** Pane sizes and zoom are saved in the browser and restored on refresh.

## [0.3.0] - 2026-11-03

### Added

- **Split at guide.** A Shot marker with an accepted guide can split its clip there. The guide becomes the first clip's Last and the second clip's First, joined by Continue, so one clip ends exactly on the image and the next starts from it. Both halves round up to the frame grid. Later timestamps, guides, plate changes, pinned cast moments and chosen memories move to the second clip. A half that still mentions references gets FLF2VA + cached RefMods.
- **Tests.** `node tests/run.mjs` runs the browser-module tests and the package tests. A server-agreement test checks that the render code reads a browser split the way the browser intends.

### Fixed

- **Split before Shot N keeps Shot guides.** A guide accepted on a Shot marker now moves to its shot's new number in the second half. Before, it pointed at a shot that no longer existed and was dropped from the render.

## [0.2.1] - 2026-11-03

### Added

- **Free aspect ratio for configured Timeline workflows.** A configured workflow can render at another aspect ratio while keeping its saved pixel count, for example 3:4 instead of only its saved 1920x1088. Sizes snap to multiples of 32 and stay within 5% of the saved pixel count. Delivered videos are checked against the production size.
- **Box reuse on project updates.** An asset that only one box reads (a guide, plate, timed audio clip, voice clip, Studio picture or reference replacement) now counts only toward that box's identity. Replacing one box's guide re-renders that box instead of the whole film.

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

[0.3.0]: https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/releases/tag/v0.3.0
[0.2.1]: https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/releases/tag/v0.2.1
[0.2.0]: https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/releases/tag/v0.2.0
[0.1.0]: https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/releases/tag/v0.1.0
