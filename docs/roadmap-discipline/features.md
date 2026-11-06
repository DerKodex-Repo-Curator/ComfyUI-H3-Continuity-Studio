# Regeneration overlap investigation

**Status:** Verified locally; awaiting integration
**Current Phase:** Phase 13: P-H3 still prompt instructions

## Phase Ledgers

- [Incompatible saved overlap](phases/2026-11-06-incompatible-overlap.md)
- [P-H3 still prompt instructions](phases/2026-11-04-ph3-still-prompts.md)

Prior merged work: [P-H3 node ledger](phases/2026-11-04-ph3-image-still.md). Its inherited pre-merge recovery is superseded by this follow-up; no native generation is requested.

## Recovery State

```json
{
  "version": 1,
  "revision": 18,
  "phase": "Phase 13: P-H3 still prompt instructions",
  "active_features": [
    "IO4"
  ],
  "focus_feature": "IO4",
  "goal": "Create and merge PR, publish v0.17.0, and fast-forward development and installed ComfyUI node checkouts without restarting.",
  "done_when": "PR merged; annotated release tag and GitHub release point at merge commit; both checkouts equal released main; local work preserved.",
  "last_completed": "IO3 Project settings/new generations verified; combined164JS +307Python, strict docs, browser1440/390px and native/attached host smoke, syntax/diff/roadmap checks pass.",
  "in_progress": "Implementation committed ba832c0; latest main e154bb1 integrated with conflicts resolved, v0.17.0 changelog prepared. Fresh175JS/332Python, browser and strict docs pass. PR creation next.",
  "next": {
    "action": "Commit integration/release metadata, push branch and create PR against main.",
    "reason": "Fresh current-main verification passes; release is authorized."
  },
  "files": [
    {
      "path": "docs/roadmap-discipline/phases/2026-11-06-incompatible-overlap.md",
      "state": "IO1/IO2/IO3 verified; review findings recorded"
    },
    {
      "path": "docs/superpowers/plans/2026-11-06-new-generation.md",
      "state": "Executed plan"
    },
    {
      "path": "h3_continuity/regeneration.py",
      "state": "Selective recovery preflight and commit"
    },
    {
      "path": "h3_continuity/generations.py",
      "state": "Fresh generation and history"
    },
    {
      "path": "tests/browser/new_generation.py",
      "state": "Reproducible isolated browser QA"
    }
  ],
  "repository": {
    "branch": "fix/incompatible-render-overlap",
    "head": "3b2d569",
    "dirty": [
      "Roadmap investigation checkpoint only."
    ],
    "dirty_hash": "unrecorded"
  },
  "verification": {
    "required": "full tests; browser smoke; strict docs; PR merge/tag/release; both checkout HEADs",
    "last_run": "node tests/run.mjs; browser smoke; strict docs; syntax/diff checks",
    "status": "passed",
    "detail": "175 JavaScript +332 Python, no skips/failures. Browser native/attached desktop/mobile and strict docs pass. Added guide-frame success/failure and consent stamp integration regressions. Remote integration/tag/checkout synchronization pending."
  },
  "blockers": [],
  "reload": [
    "docs/roadmap-discipline/features.md",
    "docs/roadmap-discipline/phases/2026-11-06-incompatible-overlap.md",
    "docs/superpowers/specs/2026-11-06-incompatible-overlap-design.md",
    "docs/superpowers/specs/2026-11-06-new-generation-design.md"
  ]
}
```
