# Changelog

All notable changes to H3 Continuity Studio are recorded here. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Keep the first pass, re-render the second.** The new **H3 Disk Cache** node goes after the first-pass sampler and saves its result on disk, keyed by the Timeline's `positive`, `latent` and `seed` and by the settings above the sampler. Render the whole Timeline without a second pass, turn the second pass on, and render again: every clip loads its first pass from disk and goes straight to the second pass. Its `info` output says why a result was sampled again or could not be cached. See [Keep the first pass](guide/output/first-pass-cache.md).
- **H3 Save Segment `guide_frames`.** Connect the first-pass decode, and a continuing clip is guided from the last frame of the clip before as it was sampled, not as finished, so a second-pass change no longer changes every later clip's first pass.

## [0.15.0] - 2026-11-06

### Added

- **Named checkpoints with videos.** In **Saved stories**, **Save checkpoint…** preserves the current workflow, Timeline, rendered videos and takes as a named snapshot, separate from automatic versions. Later edits and renders cannot overwrite it. Loading a checkpoint opens an independent editable copy with its own media. Checkpoints and restored copies use additional disk space; existing versions are kept.
- **Optional autosave.** The **Autosave** checkbox in **Saved stories**, also available in **H3 Continuity → Story → Autosave** settings, persistently disables background Story and Timeline saving across workflows, including attached projects. Explicit actions that require saving still save their state. Checkpoint saving captures local edits directly, without first restoring another workflow's autosave.

## [0.14.0] - 2026-11-06

### Added

- **Video so far.** Before every clip has rendered, the Viewer's switch reads **Video so far · 5/90** and plays the clips rendered from the first one on, joined with their bridges and the ticked audio clips (or H3's audio), so a timing problem against the soundtrack shows after a few clips instead of after the whole render. It is built in the background, grows as clips render, keeps playing from the same moment when it grows, and is saved as `<name>_sofar.mp4`.
- **Playhead.** A playhead follows the playing video along the ruler, the clips and the audio lanes, holding at a cut while an inserted bridge plays. Click or drag the ruler to play from that moment.
- **Detailed waveforms.** Audio clips draw their file's waveform at any zoom, decoded once per file in the browser, instead of a 256-point outline.
- **Snap to beats.** **Detect beats** finds the beats of the audio lanes and draws them under the waveforms; with **Snap to beats** ticked, dragging a clip's edge lands it on the nearest beat (Shift drags freely).

## [0.13.1] - 2026-11-06

### Fixed

- **The Studio no longer changes clip lengths behind your back.** Every edit (a prompt, a remembered moment, a setting) re-checked all clip lengths and quietly cut any clip over 362 frames, or over the continuing limit after `context_frames` changed, down to the limit, which moved every later clip off its recording or beat map. Lengths now stay as saved, a clip over the limit shows the problem instead, and the Studio keeps a Timeline's `max_frames` (it used to drop it on save) and lets clips reach it.
- **Errors no longer suggest changing a clip's length to fit something that depends on it.** A remembered moment past its source clip now says which frames that clip plays, and a plate change or guide past a clip's end says to move it earlier rather than lengthen the clip. Where a length change is one of two fixes (dropped frames before a continuation or a bridge, too few frames to carry), the message says it moves every later clip, and offers a cut or a replacement bridge first. The agent skills now say that lengths belong to the author: an agent moves the dependent memory, guide or prompt timing, or asks before changing a length.

## [0.13.0] - 2026-11-06

### Changed

- **Rendered clips no longer disappear from the Timeline.** A clip whose prompt, settings or remembered clip changed after it rendered is now *outdated*: it keeps its thumbnail and video, plays in the full video, and shows what changed in its tooltip. **Render N remaining** renders only clips with no take; regenerate an outdated clip from its own button.
- **Saved takes follow their clip, not its position.** Inserting, removing or moving a clip no longer marks every later clip unrendered, rendering a clip moves only that clip's earlier take to `takes/` (never the clips after it), and takes of removed clips stay in place.
- **The full video builds in the background.** Status checks no longer wait for the encode (about 10 minutes for 88 boxes), which made every clip look unrendered until it finished. A failed or timed-out status check keeps the last known clips on screen.
- **Clips of different formats join.** The full video takes the best of its clips: the highest frame rate (24 fps clips repeat frames beside interpolated ones, keeping their duration), HDR when any clip is HDR (SDR clips converted), and the largest size. Only a different aspect ratio is refused. The continuity check reads interpolated clips too.
- **One saved story, not many copies.** Loading a saved story continues that story, with its own sequence folder and renders, even when this workflow's wiring differs; clips whose render settings changed show as outdated. The story picker groups entries that share a sequence folder or a title as versions of one story, and each version shows its folder and how many clips it has rendered.

### Added

- H3 Save Segment has a `codec` choice: H.264 (default, unchanged) or HEVC. HEVC saves 10-bit Main10 for HDR, tagged `hvc1` so Apple players show HLG, still without B-frames so segments join by packet copy. A re-encoded full video keeps the segments' codec.

### Fixed

- **Full video of frame-interpolated boxes.** A box saved at a higher frame rate (for example 48 fps after interpolation) played only the first half of its clip in the full video, the partial video and replacement previews, so each scene changed before it ended and the audio drifted. Box windows are now converted to each clip's own frame rate. Rebuild the full video of an interpolated story to fix it.
- **Render N remaining** no longer puts every run in ComfyUI's queue at once. Each queued run renders the next box that needs it, so when one run failed (a 70-box story ran the machine out of memory), every run behind it retried the same box and failed the same way. Render now keeps 3 runs in ComfyUI's queue, adds one as each succeeds, and stops at the first failed or interrupted run, taking its own waiting runs out of the queue. The setting **Runs kept in ComfyUI's queue while Render all works** changes the number; 0 restores the old behavior. Keep the page open while a long Render works.

[Changes since v0.12.10](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.12.10...v0.13.0).

## [0.12.5] - 2026-11-05

### Fixed

- P-H3 Studio stills default to 8 MP at the workflow's aspect ratio instead of inheriting a small video canvas. The generator offers 4 MP and custom dimensions; explicit still-size requests remain authoritative.
- P-H3 reference pictures retain their original pixels and aspect before native conditioning, including the first character sheet. Cast roles, picture titles and saved descriptions reach the image prompt.
- P-H3 native video prompts without authored snapshots require still-prompt preparation or manual still text. Snapshot prompts retain subject designs and scene style instead of dropping them while keeping a whole video action.

[Changes since v0.12.4](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.12.4...v0.12.5).

## [0.12.4] - 2026-11-05

### Fixed

- The Viewer shows a live render preview only when its rendering box is selected. Selecting another box shows that box's video or empty state.
- First and Last frame guides are recognized as endpoints after converting to FLF2VA, including clips already converted. Accepting an endpoint guide replaces a free guide on the same frame.
- Removing, moving or uploading Frame guides now records an Undo step.
- P-H3-Image Still recipes now accept empty autogrow image sockets, so the Timeline can supply still references without manual image connections.

[Changes since v0.12.3](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.12.3...v0.12.4).

## [0.12.3] - 2026-11-05

### Fixed

- **Shot thumbnails on the Timeline now start where their Shot starts.** A Shot at 00:01.500 no longer paints over the first 1.5 s of its box: each Shot thumbnail spans from its own start to the next Shot (or the end of the box). Boxes whose Shots sit too close together keep the earlier packed layout.

[Changes since v0.12.2](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.12.2...v0.12.3).

## [0.12.2] - 2026-11-04

### Fixed

- Story's image planner, snapshot writer and still-prompt preparation now use Pruna P-H3-Image prompting guidance when that still generator is selected: concrete medium and composition, directional lighting, exact requested text and explicit reference edits, without video prompt markup or quality-word padding.

[Changes since v0.12.1](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.12.1...v0.12.2).

## [0.12.1] - 2026-11-04

### Fixed

- **Revision tags no longer split a saved story.** A trailing revision tag such as ` · r2` or ` · r3 · r3` is ignored when saved stories are grouped, so "Heavy Things Fall Up v07 (one story) · r1" and "· r2" are versions of one story. Before, each tag made a group of its own.

[Changes since v0.12.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.12.0...v0.12.1).

## [0.12.0] - 2026-11-04

### Changed

- **Saved stories are grouped.** The Saved stories list now has two selectors: the story, then its version. Saved entries with the same title (ignoring case and spacing) are versions of one story, so a story saved many times no longer fills the list. Versions are numbered from v1, newest first, and the one open in this workflow is marked *open now*. **Delete permanently** is now **Delete version** and removes only the selected version. Nothing is renamed or moved on disk.

### Added

- **Rename story and Delete story.** **Rename story** shows a name you choose in place of the title; the story is still found by its title, so new saves with that title join it, and an empty name goes back to the title. Names are kept on the server in `user/__h3c_state`. **Delete story** removes every version and its generated media after one confirmation; if a version cannot be deleted (for example a render is running) it stops there and says how many were removed.

[Changes since v0.11.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.11.0...v0.12.0).

## [0.11.0] - 2026-11-04

### Added

- **P-H3-Image Still node.** One node generates Timeline stills with Pruna AI's P-H3-Image (derived from MiniMax H3). Select the installed `p-h3-image` model, text encoder and VAE, connect its `still_recipe` output to the Timeline, and generate First, Last and Shot candidates in the Studio; no sampler graph or bindings to write. It expands into the official ComfyUI workflow (8 steps, euler, no CFG), takes up to 8 reference pictures as `<Picture N>` with the scene placed first, and has an optional prompt upsampler (off by default, not with references yet). A video render never runs it. Missing files, an old ComfyUI, bad sizes and too many references give messages that say what to fix. New: `examples/ph3_image_story_studio.json` and the guide page *Stills with P-H3-Image*, which also covers the license (the weights exclude the EU, UK, South Korea and the US without a separate MiniMax license). Existing Still Recipe setups are unchanged.

[Changes since v0.10.1](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.10.1...v0.11.0).

## [0.10.1] - 2026-11-04

### Changed

- **Long continuing chains guide: the model matters most.** The burn table is now labelled as FastH3 omniref int8's. A new table shows the same chain on MiniMax REF2VA (int8 ConvRot and bf16, with the ref2v turbo LoRA v1.1): it barely burns (clip 6 texture 1.19 against 2.04), and the anti-burn LoRA through **H3 Continuation Model** is safe there at 0.5 (no cut, clip 6 at 1.04). FastH3 v2 with turbo LoRA v1.0, which the Story Studio examples use, did not burn either (clip 6 at 0.97), but clip 2 cut to a closer framing at the first join, with or without the anti-burn LoRA, with the examples' res_multistep sampler as well as euler, and on a second seed.

[Changes since v0.10.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.10.0...v0.10.1).

## [0.10.0] - 2026-11-04

### Added

- **Undo, redo and history.** Studio controls and keyboard shortcuts step through Timeline edits. History lists named states and jumps directly backward or forward. Typing in one field and dragging a clip form one edit; making a new edit after a jump replaces the redo branch. The latest 100 edits stay available until the project/workflow changes or the page reloads. On phones, the controls are under More.
- History restores clips, prompts, guides, Cast, pictures, references, audio, timed text and Timeline settings through the existing save path. Writer results applied to the Timeline are included; live job receipts keep following the server. Independent Story inputs, graph wiring, job cancellation and permanent file deletion remain outside this history.

- **Partial video while repainting.** Until every clip of a Timeline that splits a video is rendered, the Studio's **Full video** and **Download video** use `<name>_partial.mp4`: the rendered clips, and the split video's own frames and sound for the others, at the Timeline's full length. The Timeline node saves the split video at render size (`<name>_source.mp4`) for it.

[Changes since v0.9.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.9.0...v0.10.0).

## [0.9.0] - 2026-11-04

### Added

- **Audio in FLF2VA + cached RefMods.** A clip with this switch on no longer falls back to REF2VA because it mentions audio or has an audio-lane clip under it. The raw audio is encoded by the H3 audio VAE into the same reference REF2VA uses and numbered before any audio RefMods, so **Convert to FLF2VA** now works on clips with a soundtrack. Raw video still needs REF2VA. The Timeline needs its audio VAE connected for this.

[Changes since v0.8.1](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.8.1...v0.9.0).

## [0.8.1] - 2026-11-04

### Fixed

- **Frame guide list layout.** Each guide in the Shots tab is a card with its thumbnail, name, **Frame** field and **Remove**. **Guide another frame** is its own drop box. A guide from an older project that still renders at its saved frame after its shot was removed reads **Frame guide** instead of **Removed Shot N**.

[Changes since v0.8.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.8.0...v0.8.1).

## [0.8.0] - 2026-11-04

### Added

- **Guides at any frame.** In a clip's **Shots** tab, **Guide another frame** uploads a guide for a chosen frame without adding a `[Shot N]` line, and every listed guide has a **Frame** field that moves it. A guide whose Shot marker was removed now reads **unused** instead of claiming a frame, and can be given a frame again.
- **Convert to FLF2VA.** A REF2VA clip's **Settings** tab has a button that turns on **FLF2VA + cached RefMods**: its First and Last frames become the start and end frames, and its images become cached RefMods. When the clip mentions a raw video or raw audio, which the Studio cannot convert to RefMods, or a fresh clip has no First frame, the button is disabled and says why.
- **Drop images on guide targets.** Dropping an image file on a First, Last or Shot marker, on the frame panel's image area, on **First frame** or **Last frame** in **Settings**, or on **Guide another frame** uses it as that guide.
- **Texture drift and holds in the continuity check.** Drift also compares fine-detail energy with the scene's first clip and names a rise of 25% or more ("Drift: 104% grainier than box 1."); a drop is stored but not named, since motion blur lowers it too. The check reports still holds of two or more near-still frames, including the step into a continuing clip ("Holds still: 3 frames at the join."). Holds enable Retake.
- **Settings for long continuing chains** (off by default; in the Studio under **Project settings → Long continuing chains**, or as Timeline JSON): `context_noise` (paired context noise on the carried frames; on a six-clip chain, clip 6's texture rose to 1.75x instead of 2.04x, about 10% slower), `continuation_guide: false` (no last-frame guide at the first new frame; removes the 3-frame join hold in moving shots) and `audio_feather` (the last carried audio ticks regenerate). See *Long continuing chains* in the guide.
- **H3 Sigmas Tail** node: raises the last noise levels before zero, optionally on continuing clips only (texture 1.93x alone, 1.67x with context noise).
- **H3 Continuation Model** node: samples continuing clips and bridges with another model, for a continuation LoRA.
- **Take ratings, tags and lineage.** Each take has five stars and a short tag (`takes_marks.json`), and a continuing take says which take of the clip before it came from.
- **Fork as a copy** in the Studio's **Project settings**: downloads the generation (the way back), then continues on a copy with every render and take.
- **`video_slices`** (**Split @video1 across clips** in the same Studio section): each clip receives only its own window of a long reference video and its soundtrack, for repainting a long video clip by clip.
- **Measurement tool.** `tools/measure.py` prints texture, colour drift and holds per saved segment; scenario S5 (one long reference video split across clips) joins the others in `examples/prefixstream_scenes/`.
- External Timeline preparation is `external-instructions-v10` and lists the new fields; the Timeline API schema declares them.

### Changed

- The Studio's **Feedback** button is now **Revise story**: it asks the Story writer to change the written story and doesn't send feedback to the node's author.

### Fixed

- **Project settings in narrow windows.** Below 900 px the Inspector and References panels float over the page that **Project settings** (and Story, Cast, Pictures and RefMods) opens, which made the button look like it did nothing. Opening one of those pages now closes them.

[Changes since v0.7.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.7.0...v0.8.0).

## [0.7.0] - 2026-11-04

### Added

- **Smoke comparisons.** `tools/smoke.py` runs a scene with named variations of Timeline settings, prompts or graph nodes, records each run's timing and status, and copies the full videos with duration, frame-count and audio-presence metadata into a JSON summary. When every variation produces a video, it also creates a side-by-side comparison. Use `--arm` to select variations and `--cap` to bound each render request.
- **Four comparison scenarios.** `examples/prefixstream_scenes/` includes a talking continuation chain, a walking phone conversation, a rooftop landing and two alternative story branches, with smoke specifications under `smoke/`.

### Removed

- **Split at guide.** Splitting inside a shot repeated its opening action in both prompts, which could restart a camera move. Use **Split before Shot N** at a timed shot boundary; the second clip starts with a **Cut**. First, Last and interior frame guides remain available, and saved projects keep their existing boxes, prompts, guides and joins.

### Fixed

- **Portable smoke output paths.** The smoke tool defaults to `$COMFY_ROOT/output` when `COMFY_ROOT` is set; otherwise it requires `--output`, instead of assuming one machine's folder.
- **Portable ComfyUI test setup.** The test runner supplies `COMFY_ROOT` from a detected Windows portable ComfyUI installation when the variable is unset, so CPU tests can load ComfyUI without manual environment setup.

[Changes since v0.6.0](https://github.com/KadoBOT/ComfyUI-H3-Continuity-Studio/compare/v0.6.0...v0.7.0).

## [0.6.0] - 2026-11-04

### Added

- **Replacement bridges (unavailable).** A Timeline can describe a bridge that *replaces around the cut*: H3 regenerates a reviewed region of the two clips with exactly as many frames, so the full video keeps its length and recordings stay in sync. In tests with real generations every candidate still jumped at its joins, so this version ships them switched off: nothing renders or plays a replacement, the original cut plays, and the Studio only offers to remove one. See [Joins and bridges](guide/continuity/joins-and-bridges.md#replacement-bridges).
- **Dialogue cues.** A recording's exact words at its own times, with speaker, on-screen or voiceover portrayal and a check against the recording. Import them from a timed transcript, take them from the Story or type them. Clips speak the cues in their window as `<d>` lines, and replacements keep on-screen speech and footage you mark. See [Dialogue cues](guide/sound/dialogue.md).
- **Locked recordings.** An uploaded audio clip can be locked to the sequence clock: no bridge may add time inside it, so its cuts stay cuts, and the Timeline names any inserted bridge or setting that would move the picture off it.

### Fixed

- **A dialogue cue span with a non-numeric start** is now refused with an *H3 Timeline: dialogue …* message instead of an internal `TypeError`.
- **Visual memory is judged with the audio lanes and cues already read.** `parse` checked each box's memory before the Timeline's audio lanes and dialogue were loaded, so every cue looked missing.
- **Checking a dialogue cue works on plain http.** The check key needed `crypto.subtle`, which only exists on HTTPS or localhost; ComfyUI opened on a LAN address could not tick **Checked**.

### Changed

- **Visual memory at a cut with speech.** When someone speaks on either side of a cut, the clip after it remembers the five frames before the cut instead of the full preceding video. H3 copied that video's lip movement onto the new shot, so the new clip's lines went out of sync. Such clips need a render. See [Visual memory](guide/continuity/visual-memory.md#how-it-works).
- Timelines that use replacements, cues or locks list them in `requires`. From this version on, a reader that doesn't know a listed feature stops with *this Timeline needs a newer H3 Continuity* instead of misreading the file. Existing bridges keep their meaning: a bridge without `mode` still inserts time.

### Known limits

- Replacement bridges are shipped switched off: every real candidate still jumped at its joins, so the original cut plays.
- An inserted bridge does not move dialogue cues. A recording that plays in the full video and is not locked drifts from the picture after the bridge by the bridge's length; a locked recording only gets a warning. Lock the recording and keep the cut.

## [0.5.0] - 2026-11-04

### Added

- **Agent skill pack.** `skills/` now holds seven skills that work together. `h3-continuity-video` is the entry, and six scoped skills cover joins and visual memory, timing, references and guides, sound and text, Story and Cast, and the API. Together they describe every feature, including visual memory, plates, RefMods, takes, the continuity check, long clips and voice clips, which the earlier single skill did not mention. `GET /h3c/timeline/instructions` serves the whole pack as `skills` (`instructions_revision` `external-instructions-v8`), and `python skills/install.py` links it into the agent skill folders on this computer.
- **22-frame context.** `context_frames` now offers 22 (0.9 s) next to 39, 90 and 141, in the node combos, the Timeline API schema and limits, and external Timeline preparation (`instructions_revision` `external-instructions-v9`). A continuing box adds the same new frames at 22 as at 39 and generates 17 fewer, so sampling is slightly cheaper; 39 stays the default because 0.9 s carries less motion into fast action.
- **Comparison tools.** `tools/side_by_side.py` lays clips out in a row on one clock with labels and one audio track per clip, and `tools/render_scene.py` renders a scene file box by box on a ComfyUI server with a time cap. `examples/prefixstream_scenes/` holds the memory and continuation test scenes they were used with.

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
