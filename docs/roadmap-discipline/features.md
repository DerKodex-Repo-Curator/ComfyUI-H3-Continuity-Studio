# Guide-split prompt continuity roadmap

**Status:** In Progress
**Current Phase:** Phase 3: Editing history release

## Phase Ledgers

- [Guide-split prompt continuity design](phases/2026-11-04-guide-split-prompt-continuity.md)
- [Editing history release](phases/2026-11-04-editing-history-release.md)

## Recovery State

```json
{
  "version": 1,
  "revision": 11,
  "phase": "Phase 3: Editing history release",
  "active_features": [
    "EH2"
  ],
  "focus_feature": "EH2",
  "goal": "Port editing history to current main, merge its PR, and publish v0.10.0.",
  "done_when": "PR merged; tag points at its merge commit; v0.10.0 published and verified.",
  "last_completed": "Recovered current main 172fe5c and confirmed historical PR19/v0.7.0 completed.",
  "in_progress": "Scoped history implementation rebased onto main 47c1d43, preserving partial export. Final 84 JS + 192 Python tests, strict docs, syntax, diff and desktop/mobile browser checks pass. UTF-8 conflict-resolution correction verified. Release notes prepared under ignored .tmp.",
  "next": {
    "action": "Commit final release metadata and UTF-8 corrections, push feat/editing-history, create/link PR, and inspect checks. After green checks merge with a merge commit and publish v0.10.0 at that merge commit using .tmp/release-notes.md.",
    "reason": "User authorized publication; no source or verification issues remain."
  },
  "files": [
    {
      "path": "web/h3c_history.mjs",
      "state": "new"
    },
    {
      "path": "web/h3c_timeline.js",
      "state": "modified"
    },
    {
      "path": "web/h3c_studio.mjs",
      "state": "modified"
    },
    {
      "path": "web/h3c_timeline_editor.mjs",
      "state": "modified"
    },
    {
      "path": "tests/js/history.test.mjs",
      "state": "new"
    },
    {
      "path": "CHANGELOG.md",
      "state": "v0.10.0"
    },
    {
      "path": "guide/getting-started/studio-tour.md",
      "state": "updated"
    }
  ],
  "repository": {
    "branch": "feat/editing-history",
    "head": "5f44fb9f41a6",
    "dirty": [
      "CHANGELOG.md",
      "docs/roadmap-discipline/readiness-checklist.md",
      "web/h3c_studio.mjs",
      "web/h3c_timeline.js"
    ],
    "dirty_hash": "25ce256f7d478722f891a10c417488a6c0adc893dc6faa13a289ad3b600c2d43"
  },
  "verification": {
    "required": "node tests/run.mjs; isolated desktop/mobile browser smoke; strict docs build; git diff --check; PR checks; merged tag and published release verification",
    "last_run": "node tests/run.mjs; node .tmp/history-smoke.mjs; uv run --with-requirements requirements-docs.txt mkdocs build --strict; syntax and diff checks",
    "status": "passed",
    "detail": "84 JS + 192 Python pass/no skips; isolated real controls/host methods pass with mocked services, desktop/mobile; strict docs, syntax and diff checks pass. Remote PR/tag/release actions pending."
  },
  "blockers": [],
  "reload": [
    "docs/roadmap-discipline/features.md",
    "docs/roadmap-discipline/phases/2026-11-04-editing-history-release.md"
  ]
}
```
