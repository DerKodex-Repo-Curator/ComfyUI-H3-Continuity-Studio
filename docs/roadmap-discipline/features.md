# Guide-split prompt continuity roadmap

**Status:** In Progress
**Current Phase:** Phase 2: Release

## Phase Ledgers

- [Guide-split prompt continuity design](phases/2026-11-04-guide-split-prompt-continuity.md)

## Recovery State

```json
{
  "version": 1,
  "revision": 8,
  "phase": "Phase 2: Release",
  "active_features": [
    "GSP2"
  ],
  "focus_feature": "GSP2",
  "goal": "Create and merge the guide-split removal PR and publish v0.7.0 with all changes since v0.6.0.",
  "done_when": "PR is merged, v0.7.0 tag resolves to its merged commit, and GitHub release is published with the complete cumulative changelog.",
  "last_completed": "Cumulative v0.7.0 changelog complete; final CPU suite 51 JS + 130 Python passed/no skips; isolated uv MkDocs strict build and diff checks passed.",
  "in_progress": "Release content verified. PR body and release notes prepared under ignored .tmp. Ready to commit/push and create PR; no release tag exists.",
  "next": {
    "action": "Commit and push the verified branch; create and link its PR, then inspect checks and merge readiness.",
    "reason": "All local checks pass; user explicitly authorized publishing and merging."
  },
  "files": [
    {
      "path": "CHANGELOG.md",
      "state": "Complete v0.7.0 cumulative changes since v0.6.0"
    }
  ],
  "repository": {
    "branch": "design/guide-split-prompt-continuity",
    "head": "469771e042e0",
    "dirty": [
      "CHANGELOG.md",
      "docs/roadmap-discipline/",
      "docs/superpowers/plans/2026-11-03-guide-split.md",
      "docs/superpowers/specs/2026-11-03-guide-split-design.md",
      "guide/build/frame-guides.md",
      "guide/build/timeline.md",
      "skills/h3-continuity-joins/SKILL.md",
      "skills/h3-continuity-video/SKILL.md",
      "tests/README.md",
      "tests/js/emit_guide_split.mjs",
      "tests/js/emit_shot_split.mjs",
      "tests/js/guide_split.test.mjs",
      "tests/js/guide_split_editor.test.mjs",
      "tests/js/guide_split_fixtures.mjs",
      "tests/js/shot_split.test.mjs",
      "tests/js/shot_split_fixtures.mjs",
      "tests/test_guide_split_server.py",
      "tests/test_shot_split_server.py",
      "web/h3c_frame_images.mjs",
      "web/h3c_guide_split.mjs",
      "web/h3c_shot_split.mjs",
      "web/h3c_timeline.js",
      "web/h3c_timeline_editor.mjs"
    ],
    "dirty_hash": "4df25aa4d0ce1de296c1b3f220d4726b41793f8fc347731ef8b4f7bdbd8405ee"
  },
  "verification": {
    "required": "node tests/run.mjs; git diff --check; inspect PR checks and merge state; verify release tag resolves to the merged commit and published release notes cover v0.6.0 onward",
    "last_run": "node tests/run.mjs; git diff --check; inspect PR checks and merge state; verify release tag resolves to the merged commit and published release notes cover v0.6.0 onward",
    "status": "passed",
    "detail": "Local release verification: node tests/run.mjs 51 JS + 130 Python pass/no skips; uv run --with-requirements requirements-docs.txt mkdocs build --strict passed; git diff --check passed. Remote PR/tag/release checks pending."
  },
  "blockers": [],
  "reload": [
    "docs/roadmap-discipline/features.md",
    "docs/roadmap-discipline/phases/2026-11-04-guide-split-prompt-continuity.md"
  ]
}
```
