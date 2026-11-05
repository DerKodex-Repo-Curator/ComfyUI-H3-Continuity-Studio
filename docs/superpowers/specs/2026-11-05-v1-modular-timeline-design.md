# v1.0.0 modular Timeline: design

Status: **approved 2026-11-05; amended 2026-11-05 (single node id, Guided/Full modes: user decision after planning found ~30 hard-coded `H3C_Timeline` checks, including the Timeline API).** Decisions marked *(user)* were made in the grilling rounds; *(call)* marks a decision made by the writer and open to correction. Product context: `PRODUCT.md`. Roadmap: `docs/roadmap-discipline/phases/2026-11-05-v1-modular-timeline.md`.

## Intent

New users cannot get a first working render. Feedback: a user lost 12+ hours, called the example workflows "empty templates", and others asked for a video tutorial. Verified in the repo: 9 of 12 example workflows ship an empty timeline (`{"version":1,"boxes":[]}`) or none; the 3 with boxes hold one single "mountain lake" clip; none shows continuity, the thing the pack exists for. Separately, the all-in-one **H3 Timeline** and its Studio expose every feature at once, so users cannot find features, do not know how to use them, or will never use them.

v1.0.0 fixes both: **a first success in one load-and-run, and features that appear only when the user opts in.** Nothing about what the engine renders changes.

## Goals

1. *(user)* **Acceptance test:** a stranger loads `Hello H3`, selects their model files and clicks the node's existing **▶ Render** (it queues one run per unrendered box). They get a finished two-clip video with a visible continuity join, with no other configuration, no LLM endpoint and no input pictures.
2. *(user)* Optional features are separate nodes the user plugs in on demand. The Studio shows a feature only when its node is connected.
3. *(user)* Every add-on has its own small working example, built on the first.
4. *(user)* Saved workflows keep working.
5. Native ComfyUI parts are used for wiring and settings. The Studio keeps everything positioned on the timeline. Where a native part would hurt the user, the Studio wins *(user)*.

## Non-goals

- Any change to rendering, timing, joins, memory, bridges, takes, the Timeline JSON schema or the Timeline API.
- Moving image, audio or video sockets off the Timeline core *(user: chain carries JSON and settings only)*.
- Redesigning the Studio's visual style, mobile layouts or the Story writer.
- A tutorial video or its script *(user records the video; we only keep the first example identical to what it shows)*.
- New features.

## Anti-goals

Failure even if tests pass: a first-time user still sees the old wall of tabs; the first example still needs a picture, an endpoint, or editing before it runs; a saved graph from 0.12.x fails to load or changes how it looks (it must open in Full mode); the node renders a different video than 0.12.x for the same inputs.

## Constraints

- ComfyUI V3 nodes (`comfy_api.latest`), as in `extension.py`. Desktop first, mobile layouts must not break *(user)*. Models are not bundled.
- The engine reads media through lazy sockets on the node itself (`check_lazy_status`, `fingerprint_inputs`, job ownership in `timeline_node.py`). Those stay untouched.

## Approaches considered

| | Idea | Verdict |
|---|---|---|
| A | Keep one node. Hide features behind collapsed panels. | Rejected *(user)*: no new nodes, features still undiscoverable, no plug-and-play. |
| B | **Chain `H3C_PROJECT` carrying JSON and settings only. Add-ons unlock Studio panels and carry settings. Pictures, audio and video stay on the core.** | **Chosen *(user)*.** Zero engine risk, the lazy loading is untouched. Cost: an add-on such as References is an unlock plus settings, not a socket holder. |
| C | Chain also carries media; each add-on owns its sockets. | Rejected for 1.0. Needs lazy loading, fingerprints and ownership re-plumbed across a chain, plus an equivalence suite. Revisit in 1.1 if users find B awkward. |

## Design

### Nodes

| Node | Display name | Notes |
|---|---|---|
| Core | **H3 Timeline** | Keeps the id `H3C_Timeline`, the engine and the 7 outputs. Adds one optional input, `project` (`H3C_PROJECT`). The widgets owned by add-ons (`ref_image_size`, `carry_audio`, `audio_context_frames`) become `advanced=True` in the **same positions**, so saved widget values still load *(user)*. No classic copy, nothing to hide. |
| New add-ons (3) | **H3 + References**, **H3 + Sound**, **H3 + Continuity tools** | Each: `project` in (optional), `project` out. Typing "H3 +" in search lists them. |
| Existing, unchanged | H3 Story, StoryTurn, Still nodes, P-H3-Image Still, Context Windows, Join Chain, Save Segment | Already separate. Connecting one gates its Studio panel (below). |

`H3C_PROJECT` is a small value: `{"features": [...], "settings": {...}}`. Each add-on appends its feature id and its settings. When an add-on is connected, its value for a setting replaces the core's advanced widget value *(one rule; each setting has one owning add-on)*; otherwise the widget value is used, as today. The engine function is not changed.

### Guided and Full modes *(user)*

The Studio has one more state per core node: **Guided** (shows only connected features) or **Full** (shows everything, exactly as 0.12.x). It is a node property, `h3c_ui`, saved with the workflow.

- A node created fresh in the graph (node search, the "More you can add" button, new examples) starts **Guided**.
- A workflow saved by an older version has no `h3c_ui`, so its nodes open **Full**. Nothing already saved changes.
- A Studio toggle switches modes either way ("Show all features" / "Simplify"). Switching only changes what is shown.
- Gating hides UI only. Data in a saved timeline stays intact; a hidden-but-populated feature shows a one-line notice with an "Add the node" action.

### Settings *(call)*

**H3 + References** owns `ref_image_size`; **H3 + Sound** owns `carry_audio` and `audio_context_frames`; **H3 + Continuity tools** owns none. `context_frames` stays a normal core widget (every join uses it; Context Windows and Join Chain do not set it). Add-ons show their settings as ordinary widgets.

### What "connected" means *(call)*

An add-on counts when it is reachable by links from a core's `project` input through any chain of add-ons and is **not bypassed or muted**. Each core in a graph has its own chain. H3 Story gates by being linked to that core's `story`. Context Windows and Join Chain sit downstream of the sampler and are not linked to the core, so their gate is "present and active in the graph". This difference is deliberate.

### The core's node face

The engine keeps all its media sockets on the core (non-goal above). Spike S1 (first task of the plan): can the extension collapse or hide unconnected optional sockets in Guided mode, using the supported ComfyUI frontend, without touching the lazy-loading code? If yes, a fresh core opens as clip, vae, `project` and a single reference-picture socket. **If not acceptable, work stops and the user is asked** whether to accept visible sockets with grouped, named labels, or to move to approach C for media. This is the main open risk of the design.

### Which feature belongs where *(call; the inventory below is from the code)*

| Studio part (today) | Shown when |
|---|---|
| Viewer, Timeline, project, clip tabs **Prompt** and **Settings**, join choice (continue, cut, new scene) | Always (core) |
| Pictures, RefMods, clip tab **Shots** (first and last frames, appearance plates), `@image` reference list | H3 + References connected |
| Audio lanes, Timed text, dialogue cues | H3 + Sound connected |
| Clip tab **Takes**, bridges, visual memory modes, continuity check | H3 + Continuity tools connected |
| Story, Cast | H3 Story connected to `story` |
| Frames above the 362 limit | Context Windows or Join Chain present in the graph |

Gating must hide only the UI. Data already in a saved timeline stays intact and renders as before; a hidden-but-populated feature shows a one-line notice with an "Add the node" action, so nothing silently disappears.

### Discovery inside the Studio

A quiet row, "More you can add", lists the unconnected add-ons, each with one plain sentence about what it does for the user. Its button adds the node next to the core and wires `project`. This is how features stop being hard to find. No wizard, no tour.

### How the Studio knows what is connected

It walks the graph from the core's `project` input and `story` link, as the Studio already reads the graph for stills. UI-only; no engine calls.

### Examples

New folder `examples/v1/`, each loadable and runnable after picking models:

1. **Hello H3:** core only; two boxes, the second continues the first; prompts filled in; a note node that explains each stage in H3 terms.
2. **References**, **Sound**, **Continuity tools**, **Story**, **Long clips**, **Stills:** each a small working example. Pictures for these are two or three tiny CC0 or self-made files under 300 KB in `examples/assets` *(call; the user may supply their own)*. Only the Story example needs an endpoint.

Workflows declare `models` metadata (name, URL, folder) so ComfyUI's missing-model dialog can offer downloads; the builder verifies this against the ComfyUI version supported. Existing examples stay where they are and keep working (Full mode).

`models` entries reuse the loader selections of the existing examples (`h3_timeline_fizgig_still.json`). A download URL is written only if it is verified against the official source; otherwise the entry has name and folder only, and the release notes say so. No URL is invented.

### Docs

Guide: a "Your first video" quickstart at the top that mirrors Hello H3 step for step; one short page per add-on. README points to it first.

## Verification

- **Equivalence:** the Python engine is untouched except one small settings merge in `execute`. A test over fixture timelines (plain continue, cut, new scene, memory modes, bridge, replacement, audio lanes) with the repo's existing harness proves that, with no `project` connected, the execute path is byte-identical in its outputs (conditioning, latent, segment, seed, prompt, info) to before, and that a connected add-on changes only the settings it owns. `git diff` of the Python engine is part of the review.
- **Acceptance run:** one real run of Hello H3 on the user's GPU, started by the user or with their authorization. Until it has run, the release notes say the example was validated on CPU only.
- Existing 105 JS and 230 Python tests stay green.
- Each example loads, parses and passes graph validation on CPU. Rendering needs a GPU and models; if it is not run, the release notes say so.
- Studio gating: tests with a mocked graph for each add-on connected and disconnected; a populated hidden feature shows its notice.
- Screenshot checks at desktop and mobile sizes of the core-only Studio and of one add-on connected.

## Left to the builder

Exact widget grouping and which widgets become advanced; ids, wording and copy of add-on descriptions; the "More you can add" visual design (Impeccable, Operate mode); the final example prompts; verifying the ComfyUI features relied on (advanced inputs, deprecated or hidden search, `models` metadata) in the supported version, with a fallback if one is missing; CHANGELOG and version bump to 1.0.0; migration note in the guide.

## What this design skips (ponytail)

No wizard or tour, no Option C chain, no new Timeline JSON fields, no video script, no node per feature (three add-ons instead of ~12), no second node id, no new Timeline API behaviour.
