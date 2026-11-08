# MCP adapter implementation

**Status:** MCP implementation complete
**Current Phase:** Phase 15: durable renders and stories

## Phase Ledgers

- [MCP tools and skills](phases/2026-11-08-mcp-tools-skills.md)

## Recovery State

```json
{
  "version": 1,
  "revision": 134,
  "phase": "Phase 15: durable renders and stories",
  "active_features": [],
  "focus_feature": "None",
  "goal": "Implement the approved standalone MCP adapter and current skills with tested README/docs installation instructions for Codex and Claude Code.",
  "done_when": "All eight implementation-plan tasks verified; host/adapter/skills/docs checks and client fixture evidence recorded; known client extension limits reported accurately.",
  "last_completed": "MCP1 implemented and independently reviewed; all six findings reproduced and fixed in 0f2b02f. README/docs installation and canonical seven skills delivered.",
  "in_progress": "None. Branch feat/mcp-adapter and worktree retained locally for integration.",
  "next": {
    "action": "Keep the completed branch for the user to review/integrate; no publication or live host action is authorized.",
    "reason": "Authorized implementation, documentation, verification and final review/fix gates are complete."
  },
  "files": [
    {
      "path": "docs/roadmap-discipline/phases/2026-11-08-mcp-tools-skills.md",
      "state": "MCP0 and MCP1 passing; review fixes and client limits recorded"
    },
    {
      "path": "docs/superpowers/plans/2026-11-08-mcp-tools-skills.md",
      "state": "All eight tasks and final review/fix gate checked"
    },
    {
      "path": "docs/superpowers/specs/2026-11-08-mcp-tools-skills-design.md",
      "state": "Approved implemented design"
    },
    {
      "path": "docs/MCP.md",
      "state": "Complete tool/action and client compatibility reference"
    },
    {
      "path": "guide/automation/mcp.md",
      "state": "Published installation and troubleshooting instructions"
    }
  ],
  "repository": {
    "branch": "feat/mcp-adapter",
    "head": "0f2b02f10a25",
    "dirty": [
      "docs/roadmap-discipline/readiness-checklist.md",
      "docs/superpowers/plans/2026-11-08-mcp-tools-skills.md"
    ],
    "dirty_hash": "bdc1c76ac801f3e29f4bf2f9d42d65c11b6201e2cd5c6f614fb0d0e083e590cc"
  },
  "verification": {
    "required": "uv run --project mcp_adapter python -m unittest discover -s mcp_adapter/tests -t mcp_adapter -v; node tests/run.mjs; strict guide build; module version check; Codex/Claude Code fixture connection evidence; git diff --check",
    "last_run": "Task4 red5 missing-server failures; red1 invalid catalog regression; green20 adapter tests using SDK in-memory and real stdio transport.",
    "status": "passed",
    "detail": "Final adapter67; host229 JavaScript/393 Python; strict MkDocs; module versions; compileall/import/diff checks; uv and isolated wheel launchers with spaces; Codex0.166.0 tools21/resource1; Claude2.1.316 Connected. Automatic client Skills activation remains unverified, with tested resource/filesystem fallback. Fresh independent review findings all fixed test-first."
  },
  "blockers": [],
  "reload": [
    "docs/roadmap-discipline/features.md",
    "docs/roadmap-discipline/phases/2026-11-08-mcp-tools-skills.md",
    "docs/superpowers/specs/2026-11-08-mcp-tools-skills-design.md",
    "docs/superpowers/plans/2026-11-08-mcp-tools-skills.md",
    "docs/research/2026-11-08-mcp-capability-audit.md"
  ]
}
```
