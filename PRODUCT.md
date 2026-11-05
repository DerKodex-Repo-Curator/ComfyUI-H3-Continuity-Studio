# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
ComfyUI-literate creators who are new to MiniMax H3. They know loaders, samplers and wiring, and have the H3 model files and a GPU. They do not know H3's modes, the 17k+5 frame grid, or continuity concepts. Design never explains ComfyUI basics; it always explains H3. Scripts and agents driving the Timeline API are a secondary audience that this work leaves untouched.

## Product Purpose
H3 Continuity is a ComfyUI custom node pack for authoring and rendering sequences with MiniMax H3. Clips continue each other, so a story can be built clip by clip. Success is time to first success: a new user loads one workflow, selects their models, presses Run and gets a finished multi-clip video with a visible join. Feature count is not the measure.

## Positioning
Clips that continue each other. Visual memory, joins and bridges keep people, clothes and places consistent across cuts. Story, sound and stills are supporting add-ons.

## Operating Context
Runs inside ComfyUI as nodes plus a DOM-overlay Studio editor over a Timeline JSON widget. Rendering is GPU-bound and slow, so a failed first attempt costs the user hours. Models are not bundled and have separate licences. The Story writer needs an external OpenAI-compatible endpoint that may cost money.

## Capabilities and Constraints
- v1.0.0 changes UI and UX only. Business logic and the render engine's outputs do not change.
- The always-on core is boxes, prompt, length, seed and the continue, cut or new-scene choice. Everything else is opt-in: references, sound, Story and Cast, continuity tools, long clips, stills.
- A new `H3C_PROJECT` value flows between nodes. The classic `H3C_Timeline` stays registered so saved workflows load.
- Native ComfyUI components are preferred for wiring and configuration. Positioned-on-timeline features use the Studio. User experience wins when native widgets would hurt it.
- Desktop first; the existing mobile layouts must not break.
- Frame-grid rules, timing and join semantics are domain truth, not UI to simplify away.

## Evidence on Hand
- User feedback (paraphrased): a user lost 12+ hours; example workflows are "empty templates"; others ask for a YouTube tutorial. Verified in the repo on 2026-11-05: 9 of 12 example workflows ship an empty timeline or none, and none shows continuity.
- Guide screenshots in `guide/assets/screens`, the contest demo videos linked from the README, and `docs/media`.
- Absent: usage analytics, user interviews, a tutorial video, and CC0 sample images (not yet created). Future work must not invent them.

## Product Principles
- The first run must succeed without configuration beyond model files.
- Show a feature only when the user has opted in to it.
- Explain H3, never ComfyUI.
- Prefer a native ComfyUI part when it serves the user; leave it when it does not.
- Never change what the render engine produces.
