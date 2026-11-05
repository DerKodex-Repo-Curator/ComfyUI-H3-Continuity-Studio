# v1.0.0 modular Timeline (UI/UX only)

### Phase 14: v1.0.0 design and plan

**Northstar:** A stranger loads one workflow, selects their models, presses Run, and gets a finished two-clip video with a visible continuity join. Nothing else to configure. Complexity is split into plug-and-play nodes the user adds on demand.

**Hard constraint:** Business logic does not change. Only UI and UX change. The render engine keeps consuming the same Timeline JSON and producing the same outputs.

**Process requested by the user:** superpowers brainstorming -> design spec -> implementation plan; ponytail (smallest complete change); roadmap-discipline; grilling; impeccable for UI/UX (installed globally 2026-11-05; PRODUCT.md not yet written, `impeccable init` pending). Native ComfyUI components preferred, but user experience wins when native widgets hurt it. Skills other than impeccable are read from `C:/Users/ricar/.agents/skills/` (not in Claude's skill list).

- [x] **V1-1** (State: `passing` | Verification: `docs/superpowers/specs/2026-11-05-v1-modular-timeline-design.md exists, user-approved; builder check done`)
  - *Behavior:* Brainstorm and grill to a user-approved design spec.
  - *Evidence of need:* User-reported feedback: a user lost 12+ hours; example workflows are "empty templates". Verified 2026-11-05: 9 of 12 example workflows carry `{"version":1,"boxes":[]}` or no Timeline; the 3 with boxes hold one single "mountain lake" clip; none shows continuity. Others ask for a YouTube tutorial. User has no specific feature to point at: the problem is time to first success plus undiscoverable features.
  - *Decisions (user-approved 2026-11-05):*
    1. Headline acceptance test: load one workflow, pick models, Run, get a two-clip video with a visible continuity join; shipped pre-filled with working prompts (no empty boxes); workflow `models` metadata so ComfyUI offers to download missing models.
    2. State sharing: new `H3C_PROJECT` socket type. Add-on nodes take a project in and pass it on with their slice filled in; Timeline Core reads it. Business logic unchanged.
    3. Always-on core: boxes, prompt, length, seed, continue/cut/new-scene. Opt-in nodes: references and pictures, first/last frames, audio lanes, dialogue and timed text, bridges and transitions, visual memory, takes, continuity check, Story, Cast, context windows, stills.
    4. `H3C_Timeline` stays registered as legacy so saved workflows load; new nodes are the default in search and examples.
  - *Open (next grilling round):* where each add-on's editing UI lives (own node body vs Studio panel appearing when connected); sample asset size/licence; YouTube tutorial scope; impeccable `init` interview (PRODUCT.md); node naming/categories; migration path from legacy.
  - *Round 2 decisions (user, 2026-11-05):* Studio is the single editor; panels show only for connected add-ons. Three new add-ons (References, Sound, Continuity tools) plus existing Story, Context Windows, Join Chain and Stills nodes. Hello H3 example is core-only (no pictures, no endpoint). Core takes the name H3 Timeline; old node becomes H3 Timeline (classic), hidden from search. User records the tutorial video. H3C_PROJECT carries JSON and settings only; media sockets stay on the core (engine lazy loading untouched).
  - *Done:* PRODUCT.md written; spec `docs/superpowers/specs/2026-11-05-v1-modular-timeline-design.md` written and builder-checked; the builder's answers are in the spec as marked calls.
  - *Next:* User reviews and approves the spec. Main risk: spike S1 (hide unconnected sockets on the core).

- [x] **V1-2** (State: `passing` | Verification: `docs/superpowers/plans/2026-11-05-v1-modular-timeline.md exists, user-approved`)
  - *Behavior:* Implementation plan via superpowers:writing-plans, minimal per ponytail. No code until V1-1 and V1-2 are approved. Implementation features get added to this ledger after plan approval.
  - *Done:* Plan written 2026-11-05. Spec approved (LGTM) and amended: planning found ~30 hard-coded `H3C_Timeline` checks (Timeline API profiles, native queue, takes, stills, story library, Studio); user chose to keep the id and add Guided/Full modes (`properties.h3c_ui`, absent = Full) instead of a new core id plus hidden classic.
  - *Approved:* 2026-11-05, native execution in worktree `feat/v1-modular-timeline` (from origin/main c0f3a00) so it does not block other work.

### Phase 15: v1.0.0 implementation (branch `feat/v1-modular-timeline`)

- [x] **V1-S1** (State: `passing` | Verification: headless Chromium probe vs live 8188, frontend 1.58.x, Vue nodes on, writes blocked)
  - *Answer:* `input.hidden` has no effect. `node.removeInput(k)` hides an unconnected socket (Autogrow groups and `audio_vae` included), and `graphToPrompt` stays valid. On load, the frontend reconciles inputs with the node definition and restores every missing socket, so saved files keep the full socket list, and links and prompts survive a round trip. Re-adding works with `node.addInput(name, type, {shape, tooltip, ...})` from the definition's own slot specs, and Autogrow still grows from a re-added slot. Rules for the build: re-apply hiding after configure, never re-add a name that is present, and never touch `check_lazy_status`.
- [x] **V1-S2** (State: `passing` | Verification: same probe, `/object_info` patched in the browser)
  - *Answer:* `advanced=True` on `carry_audio`, `ref_image_size` and `audio_context_frames` moves them under "Show advanced inputs"; the 0.12.x example's `widgets_values` are byte-identical before and after. An appended optional `project` input is added to old saved nodes automatically.
- [x] **V1-3** Task 2: `H3C_PROJECT`, three add-ons, core input (State: `passing` | Verification: `node tests/run.mjs` 105 JS + 240 Python)
  - *Done:* `h3_continuity/project_nodes.py` (`with_feature`, `apply_project`, `H3C_PlusReferences`, `H3C_PlusSound`, `H3C_PlusContinuity`), registered in `extension.py`. Core: three owned widgets `advanced=True` in place; `project` appended last. V1 conversion (`INPUT_TYPES`) checked.
  - *Deviation from plan step 4:* no recorded-output fixtures (no harness runs `execute` without models). Instead the 0.12.x `execute` body is renamed `_render`, unchanged (`git diff` shows only its `def` line), and a new thin `execute` merges the owned settings and forwards. `test_core_execute_unchanged_without_project` proves the forwarded arguments are identical without a project; `test_connected_add_on_changes_only_its_settings` proves only owned keys change.
  - *For Task 4:* the Studio's status requests and the Timeline API read the core widgets. The JS will mirror a connected add-on's widget values onto the core's advanced widgets so those readers see the effective value with no change.
- [ ] **V1-4** Task 3: connected-feature walk (pure JS).
- [ ] **V1-5** Task 4: Studio gating and the Guided/Full toggle.
- [ ] **V1-6** Task 5: More you can add row and the node face (socket hiding per V1-S1).
- [ ] **V1-7** Task 6: examples/v1.
- [ ] **V1-8** Task 7: docs, changelog, version.
- [ ] **V1-9** Task 8: release verification (GPU run needs the user).
