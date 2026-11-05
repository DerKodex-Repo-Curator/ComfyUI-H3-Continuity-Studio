# v1.0.0 modular Timeline: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A fresh H3 Timeline shows only core features and grows when the user plugs in add-on nodes; a pre-filled example gives a first two-clip video in one click. UI and UX only.

**Architecture:** `H3C_Timeline` keeps its id and engine. It gains an optional `project` input (`H3C_PROJECT`, JSON features and settings). Three small add-on nodes chain that value. The Studio decides what to show from the connected add-ons (Guided) or shows everything (Full, the default for older saved workflows).

**Tech Stack:** ComfyUI V3 nodes (`comfy_api.latest`), vanilla JS modules in `web/`, `node --test`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-05-v1-modular-timeline-design.md` (approved and amended 2026-11-05). Roadmap ledger: `docs/roadmap-discipline/phases/2026-11-05-v1-modular-timeline.md`.

## Global Constraints

- Business logic does not change: the Python engine's only change is one settings merge in `H3C_Timeline.execute`. No change to `rules`, `timing`, the Timeline JSON schema or the Timeline API.
- Node id `H3C_Timeline` is kept. Inputs keep their order; new inputs are appended; `ref_image_size`, `carry_audio` and `audio_context_frames` become `advanced=True` in place.
- Workflows saved before 1.0.0 open in **Full** mode; only fresh nodes start **Guided** (`properties.h3c_ui`: `"guided"` or `"full"`; absent means Full).
- Add-on ownership: References owns `ref_image_size`; Sound owns `carry_audio` and `audio_context_frames`; Continuity tools owns none. A connected add-on's value replaces the core widget's.
- "Connected" = reachable by links from the core's `project` input through add-ons, not bypassed or muted (LiteGraph mode 2 or 4). Story gates on the `story` link. Context Windows and Join Chain gate on being present and active in the graph.
- Desktop first; existing mobile layouts keep working. Studio UI changes follow `PRODUCT.md` (Operate mode: scanability and consistency, no decoration).
- No invented model download URLs. No images, audio or LLM endpoint in Hello H3.
- Test command: `node tests/run.mjs` (JS and Python, CPU). Docs: `uv tool run --with mkdocs-material --with mkdocs-glightbox mkdocs build --strict --site-dir .tmp/docs-site`. Baseline before this work: 105 JS + 230 Python pass.
- Work in a worktree on branch `feat/v1-modular-timeline` from `origin/main`. Commit per task.

## Review Focus

1. A 0.12.x workflow opens in Full mode with identical widget values and every tab (pinned in Tasks 2 and 4).
2. A muted or bypassed add-on does not unlock its panels (Task 3).
3. Two Timeline nodes in one graph each have their own chain (Task 3).
4. Switching Guided, Full, Guided loses no data; a hidden feature that holds data shows a notice, and saving does not alter the Timeline JSON (Task 4).
5. A `project` link that loops or dangles does not hang the walk (Task 3).

---

### Task 1: Spikes S1 and S2 (gate)

**Files:** scratch only; record answers in the ledger (`V1-S1`, `V1-S2` lines). No product code.

- [ ] **S1:** In the installed ComfyUI frontend (`COMFY_ROOT`), can an extension hide an unconnected optional input (an Autogrow group and `audio_vae`) on a node and keep it wireable from a workflow file, without changing `check_lazy_status`? Try `input.hidden`, shrinking the slot list on `onConfigure`, and the Studio-owned "Add socket" alternative. Record which works, in which frontend version, and what a saved workflow looks like.
- [ ] **S2:** Confirm `advanced=True` on `io.Boolean.Input` and `io.Combo.Input` appears in the frontend's advanced group and that `widgets_values` order is unchanged (load a 0.12.x workflow before and after).
- [ ] If S1 finds no acceptable way to hide sockets: **stop and ask the user** (spec: visible grouped sockets, or approach C). Otherwise continue; Task 5 uses the answer.

### Task 2: Project value, add-on nodes, core input

**Files:**
- Create: `h3_continuity/project_nodes.py`, `tests/python/test_project_nodes.py`
- Modify: `h3_continuity/extension.py` (register three nodes), `h3_continuity/timeline_node.py` (`define_schema` inputs, `execute` merge)

**Interfaces:**
- Produces: `ProjectType = io.Custom("H3C_PROJECT")`; `def with_feature(project: dict | None, feature: str, settings: dict) -> dict` (returns `{"features": [...], "settings": {...}}`, appends without duplicating, later add-ons never override a key they do not own); `def apply_project(project: dict | None, **settings) -> dict` (returns `settings` with each key in `project["settings"]` replaced; unchanged when `project` is `None`).
- Produces node ids `H3C_PlusReferences` ("H3 + References", widget `ref_image_size`), `H3C_PlusSound` ("H3 + Sound", `carry_audio`, `audio_context_frames`), `H3C_PlusContinuity` ("H3 + Continuity tools", no widgets). Each has optional input `project` and output `project`. Feature ids: `references`, `sound`, `continuity`.

- [ ] **Step 1: Failing tests** in `test_project_nodes.py`: `test_with_feature_appends_once`, `test_apply_project_none_is_identity` (`apply_project(None, carry_audio=True) == {"carry_audio": True}`), `test_connected_value_replaces_widget` (`apply_project({"features":["sound"],"settings":{"carry_audio":False}}, carry_audio=True)["carry_audio"] is False`), `test_add_on_owns_only_its_keys` (References never emits `carry_audio`), `test_schemas_have_project_in_and_out`, `test_core_inputs_keep_widget_order` (the widget-type input names of `H3C_Timeline.define_schema()` in order equal the 0.12.x list: `name,width,height,context_frames,carry_audio,ref_image_size,timeline,audio_context_frames`; `project` is last; the three owned inputs have `advanced=True`).
- [ ] **Step 2:** Run `node tests/run.mjs`; expect the new tests to fail.
- [ ] **Step 3:** Implement the two functions and three nodes in `project_nodes.py`; append `project` as the last input of the core schema and mark the three inputs `advanced=True`; in `execute`, call `apply_project` on the three settings before they are used (`project` becomes a new keyword argument, default `None`).
- [ ] **Step 4:** Add `test_core_execute_unchanged_without_project` using the repo's existing fixture-timeline helpers (`tests/python/helpers.py`, `tests/continuity_support.py`) over: plain continue, cut, new scene, a memory mode, a bridge, a replacement, audio lanes. Assert the returned `NodeOutput` equals the values recorded from the pre-change code (generate them once on `origin/main`, store under `tests/fixtures/v1_equivalence/`).
- [ ] **Step 5:** Run `node tests/run.mjs`; expect all pass. Commit `feat: H3C_PROJECT and add-on nodes`.

### Task 3: Feature walk and mode (pure JS)

**Files:**
- Create: `web/h3c_features.mjs`, `tests/js/features.test.mjs`

**Interfaces:**
- Produces: `FEATURES = ['references','sound','continuity','story','long']`; `export function connectedFeatures(graph, node) -> Set<string>`; `export function uiMode(node) -> 'guided'|'full'` (reads `node.properties?.h3c_ui`, absent is `'full'`); `export function setUiMode(node, mode)`. `graph` is a LiteGraph-shaped object (`getNodeById`, `links`), `node` a Timeline node. Maps add-on node types to feature ids: `H3C_PlusReferences`, `H3C_PlusSound`, `H3C_PlusContinuity`; `H3C_Story` through the `story` input; `H3C_ContextWindows` and `H3C_JoinChain` present in `graph._nodes`.

- [ ] **Step 1: Failing tests:** `walks a chain of add-ons in any order`; `ignores muted (mode 2) and bypassed (mode 4) add-ons`; `two Timeline nodes keep separate chains`; `a looping project link terminates`; `a dangling link id is ignored`; `story link gates story`; `Context Windows present and active gates long, muted does not`; `uiMode defaults to full when the property is absent`; `a fresh node gets guided only through setUiMode`.
- [ ] **Step 2:** Run `node --test tests/js/features.test.mjs`; expect failures.
- [ ] **Step 3:** Implement with a visited set; build fake graphs in the test file.
- [ ] **Step 4:** Run the file; expect pass. Commit `feat: connected-feature walk`.

### Task 4: Gate the Studio and add the mode toggle

**Files:**
- Modify: `web/h3c_studio.mjs` (pages `CENTER`/`FOCUS`, nav), `web/h3c_timeline_editor.mjs` (clip tabs at lines ~380–400, 603–630), `web/h3c_timeline.js` (host passes `features` and `mode` to the Studio; sets `h3c_ui='guided'` in `onNodeCreated` only when the node is not being restored from a workflow, detected in `onConfigure`)
- Create: `web/h3c_feature_notice.mjs` (the one-line notice), `tests/web/gating.test.mjs`

**Interfaces:**
- Consumes: `connectedFeatures`, `uiMode`, `setUiMode`.
- Produces: `export function visiblePages(mode, features) -> string[]` and `export function visibleClipTabs(mode, features) -> string[]`; Full returns today's lists unchanged. Guided mapping from the spec: always `viewer`, `timeline`, `project`, `box`, clip `prompt` and `box`; `pictures`, `refmods`, clip `still` need `references`; `audio`, `text` need `sound`; clip `takes` and bridge, memory and check controls need `continuity`; `story`, `cast` need `story`. `export function hiddenWithData(state, features) -> string[]` lists hidden features whose slice of the Timeline is non-empty (`audio_clips`, `pictures`, `bridges`, `memory` modes, `bible`, ...).

- [ ] **Step 1: Failing tests** (`gating.test.mjs`, using `fake_dom.mjs`): `full mode returns the 0.12.x page and tab lists`; `guided with no features shows only core`; `guided with sound adds audio and text only`; `hidden but populated feature is listed by hiddenWithData and the notice has an Add the node button`; `toggle Guided to Full to Guided leaves the Timeline JSON byte-identical`; `an old workflow without h3c_ui opens full`.
- [ ] **Step 2:** Run `node tests/run.mjs`; expect failures.
- [ ] **Step 3:** Implement the three functions; replace the hard-coded `CENTER`/`FOCUS` and tab arrays by calls to them; re-render when the mode or connections change (listen to the graph's `onConnectionsChange` and the mode toggle). Add the toggle control ("Show all features" / "Simplify") to the Studio header.
- [ ] **Step 4:** Run `node tests/run.mjs`; expect pass. Commit `feat: gate Studio panels by connected add-ons`.

### Task 5: Discovery row and the node face

**Files:**
- Create: `web/h3c_more_to_add.mjs`, `tests/web/more_to_add.test.mjs`
- Modify: `web/h3c_timeline_face.mjs`, `web/h3c_timeline.js`

**Interfaces:**
- Produces: `export const ADD_ONS = [{type, feature, title, benefit}]` (plain one-sentence benefits, H3 terms only); `export function missingAddOns(features) -> ADD_ONS[]`; `export function addAddOn(graph, coreNode, type) -> node` (creates the node, places it left of the core, links `project`; when another add-on already feeds `project`, chains behind it).

- [ ] **Step 1: Failing tests:** `missingAddOns lists only unconnected add-ons`; `addAddOn wires project and chains behind an existing add-on`; `row is absent in full mode`.
- [ ] **Step 2–4:** Implement; render the "More you can add" row at the bottom of the Studio and a compact line on the node face; apply the S1 outcome for the face in Guided mode (hide, or group and label). Run `node tests/run.mjs`; expect pass. Commit `feat: More you can add row`.
- [ ] **Step 5:** Run `/impeccable critique` on the Guided Studio (Operate mode, `PRODUCT.md`) at desktop and mobile widths using the repo's isolated Chromium harness; fix findings that change scanability or hierarchy.

### Task 6: Examples

**Files:**
- Create: `examples/v1/01-hello-h3.json`, `02-references.json`, `03-sound.json`, `04-continuity-tools.json`, `05-story.json`, `06-long-clips.json`, `07-stills.json`, `examples/assets/*` (two or three CC0 or self-made images under 300 KB), `tests/python/test_v1_examples.py`

- [ ] **Step 1: Failing tests** in `test_v1_examples.py`: every `examples/v1/*.json` parses; every node `type` is a registered node or a ComfyUI core type; `01` has at least 2 boxes, the second not `cut`, every prompt non-empty, no `H3C_Story`, no `LoadImage`/`LoadAudio`, and a note node; each of `02`–`07` contains its add-on node and its `project` link; every `models` entry has name and folder, and any `url` starts with `https://`.
- [ ] **Step 2:** Build the workflows from `examples/h3_timeline_fizgig_still.json` loaders and sampler; Hello H3 uses core only, `h3c_ui: "guided"`, a ▶ Render hint in its note, `models` metadata from the existing loader selections (URLs only if verified).
- [ ] **Step 3:** Move nothing; existing examples stay (Full mode). Run `node tests/run.mjs`. Commit `feat: v1 example workflows`.

### Task 7: Docs, changelog, version

**Files:** `guide/getting-started/first-sequence.md` (rewritten as "Your first video", mirrors Hello H3), `guide/build/add-ons.md` (one section per add-on), `mkdocs.yml` nav, `README.md` (first steps point to Hello H3), `CHANGELOG.md` (`[1.0.0]` with a migration note: older workflows open in Full mode; use the Studio toggle to simplify), skill pack text in `skills/` only where it says "press Run" or names tabs.

- [ ] Write the pages; run the strict docs build and `node tests/run.mjs`; expect green. Commit `docs: v1 quickstart and add-ons`.

### Task 8: Release verification (needs the user)

- [ ] Full `node tests/run.mjs` (expect 105 JS + 230 Python + new tests, no skips), strict docs build, `git diff --check`.
- [ ] `git diff origin/main -- h3_continuity` reviewed: only `project_nodes.py`, `extension.py`, and the settings merge and input changes in `timeline_node.py`.
- [ ] Load a 0.12.x example workflow in the live ComfyUI: Full mode, all tabs. Load `01-hello-h3.json`: Guided, core only.
- [ ] **Acceptance run on the user's GPU** (user starts it or authorizes it): select models, click ▶ Render, confirm a two-clip video with a visible join. If not run, release notes say CPU validation only.
- [ ] Record evidence in the ledger; PR, merge, tag `v1.0.0` only when the user asks.
