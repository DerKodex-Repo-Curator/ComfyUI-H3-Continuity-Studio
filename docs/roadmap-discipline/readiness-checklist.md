# Readiness — guide-split prompt continuity design

## Can Start

- Isolated branch `design/guide-split-prompt-continuity`, starting at `469771e` from origin/main. No parent-checkout changes copied. This roadmap scopes only the user's split/prompt design discussion; the other checkout's PrefixStream work stays separate.
- README installation: clone into ComfyUI/custom_nodes, run `python -m pip install -r requirements.txt` with ComfyUI's Python, restart ComfyUI. No install, live workflow change, service restart or generation authorized by this discussion.

## Can Test

- `tests/README.md` documents `node tests/run.mjs`; pure JS modules use `node --test tests/js/*.test.mjs`. Product tests use ComfyUI's Python via the runner.
- Planning verification: inspect PR #5, current split helpers/tests and guide documentation. Behavior checks can run without rendering. Visual diagnosis needs actual user render evidence; do not infer observed footage from a prompt alone.

## Can See Progress

- `features.md` and the linked design ledger record investigation, open decisions and recommendations separately from approved decisions.

## Can Pick Up Next Steps

- Recover the index and linked ledger. Investigate first, then ask a grilling frontier round. No implementation before the user confirms shared understanding.
- Design and removal are verified. The user subsequently authorized creating and merging a PR and publishing a tagged release, with a changelog covering all changes since the previous release. Release focus is GSP2; do not modify other worktrees or merge unrelated open PRs.
