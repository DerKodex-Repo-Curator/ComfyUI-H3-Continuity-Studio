# Readiness — Studio releases

## Can Start

- Current scope: approved box-bound audio design and implementation planning on `design/box-audio-range-lock`, based on local main `b7eaedc`. BA1 design approved; BA2 plan ready for user review and execution-method choice. Documentation only; no product implementation, dependency setup, rendering or deployment. Inherited IO4 release instructions are historical to this worktree; recover the box-audio-range ledger, approved design, plan and current Recovery State.

- Current worktree: fix/incompatible-render-overlap at main 3b2d569. IO1-IO3 are implemented and verified (164JS +307Python, browser desktop/mobile, strict docs); recover features.md and incompatible-overlap ledger. Prior release entries below are historical. No live service or render changes.

- Current focus: editing history on isolated `feat/editing-history`, rebased onto main `47c1d43`. The user authorized its PR, merge and v0.10.0 tagged release. Preserve the original checkout's unrelated edits. Installation remains the standard ComfyUI custom_nodes clone and `python -m pip install -r requirements.txt` with ComfyUI's Python; no live installation or inference is needed for release.
- Isolated branch `design/guide-split-prompt-continuity`, starting at `469771e` from origin/main. No parent-checkout changes copied. This roadmap scopes only the user's split/prompt design discussion; the other checkout's PrefixStream work stays separate.
- README installation: clone into ComfyUI/custom_nodes, run `python -m pip install -r requirements.txt` with ComfyUI's Python, restart ComfyUI. No install, live workflow change, service restart or generation authorized by this discussion.

## Can Test

- Editing-history release: 84 JS + 192 Python tests pass with no skips. Isolated Chromium checks actual workspace Studio controls and host restore methods against mocked ComfyUI services at desktop/mobile sizes. Strict MkDocs, syntax and diff checks pass. No live autosave HTTP or rendering claim.
- `tests/README.md` documents `node tests/run.mjs`; pure JS modules use `node --test tests/js/*.test.mjs`. Product tests use ComfyUI's Python via the runner.
- Planning verification: inspect PR #5, current split helpers/tests and guide documentation. Behavior checks can run without rendering. Visual diagnosis needs actual user render evidence; do not infer observed footage from a prompt alone.

## Can See Progress

- `features.md` and the linked design ledger record investigation, open decisions and recommendations separately from approved decisions.

## Can Pick Up Next Steps

- Current next step: review `docs/superpowers/plans/2026-11-06-box-audio-range-lock.md` with the user and record the execution method/authorization before product implementation. Native execution is recommended because the five tasks share timing interfaces. Older entries below are historical.

- Recover the index and editing-history release ledger. GSP2 is historically complete (PR #19 and v0.7.0 verified). EH2 owns the current PR/merge/release; do not merge unrelated open PRs or change the live ComfyUI installation.
