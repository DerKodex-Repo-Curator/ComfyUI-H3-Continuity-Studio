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

- [ ] **V1-2** (State: `in_progress` | Verification: `docs/superpowers/plans/2026-11-05-v1-modular-timeline.md exists, user-approved`)
  - *Behavior:* Implementation plan via superpowers:writing-plans, minimal per ponytail. No code until V1-1 and V1-2 are approved. Implementation features get added to this ledger after plan approval.
  - *Done:* Plan written 2026-11-05. Spec approved (LGTM) and amended: planning found ~30 hard-coded `H3C_Timeline` checks (Timeline API profiles, native queue, takes, stills, story library, Studio); user chose to keep the id and add Guided/Full modes (`properties.h3c_ui`, absent = Full) instead of a new core id plus hidden classic.
  - *Next:* User reviews the plan and picks subagent-driven or native execution. First task: spikes S1 (hide unconnected sockets) and S2 (advanced widgets keep positions). If S1 fails, ask the user.
