# P-H3-Image Story prompt instructions

**Status:** In Progress
**Current Phase:** Phase 13: P-H3 still prompt instructions

## Phase Ledgers

- [P-H3 still prompt instructions](phases/2026-11-04-ph3-still-prompts.md)

Prior merged work: [P-H3 node ledger](phases/2026-11-04-ph3-image-still.md). Its inherited pre-merge recovery is superseded by this follow-up; no native generation is requested.

## Recovery State

```json
{
  "version": 1,
  "revision": 6,
  "phase": "Phase 13: P-H3 still prompt instructions",
  "active_features": [
    "SP2"
  ],
  "focus_feature": "SP2",
  "goal": "Create and merge the P-H3 prompt PR, publish v0.12.2, and fast-forward the original main checkout.",
  "done_when": "PR merged; annotated v0.12.2 points at its merge commit and GitHub release is Latest; original local main equals origin/main with prior dirty work preserved.",
  "last_completed": "Integrated origin/main efb6460; fresh 105 JS + 230 Python, no skips; strict docs and diff checks pass.",
  "in_progress": "Verified code and v0.12.2 changelog ready to push. Original main diverges by local planning commit 10ce055; preserve branch and stash before alignment.",
  "next": {
    "action": "Push fix/ph3-story-prompt-instructions and open PR, then verify GitHub checks and merge.",
    "reason": "User explicitly authorized PR, merge, tagged release and main synchronization."
  },
  "files": [
    {
      "path": "h3_continuity/story_context.py",
      "state": "modified"
    },
    {
      "path": "h3_continuity/story_prompts.py",
      "state": "modified"
    },
    {
      "path": "h3_continuity/story_instructions.py",
      "state": "modified"
    },
    {
      "path": "h3_continuity/story_fast.py",
      "state": "modified"
    },
    {
      "path": "h3_continuity/story_bible_write.py",
      "state": "modified"
    },
    {
      "path": "h3_continuity/still_prompt_preparation.py",
      "state": "modified"
    },
    {
      "path": "tests/python/test_ph3_story_instructions.py",
      "state": "modified"
    },
    {
      "path": "guide/build/p-h3-image-stills.md",
      "state": "modified"
    }
  ],
  "repository": {
    "branch": "fix/ph3-story-prompt-instructions",
    "head": "ea861bd766c5",
    "dirty": [],
    "dirty_hash": "75a11da44c802486bc6f65640aa48a730f0f684c5c07a42ba3cd1735eb3fb070"
  },
  "verification": {
    "required": "full tests; strict docs build; merged PR; annotated release tag on merge commit; GitHub release Latest; local main fast-forward",
    "last_run": "node tests/run.mjs; strict MkDocs build; git diff --check",
    "status": "passed",
    "detail": "105 JS + 230 Python pass, no skips, on efb6460 + fix. Strict docs and diff checks pass. Remote release and main sync pending."
  },
  "blockers": [],
  "reload": [
    "docs/roadmap-discipline/features.md",
    "docs/roadmap-discipline/phases/2026-11-04-ph3-still-prompts.md"
  ]
}
```
