# Tests

```sh
node tests/run.mjs
```

This runs two suites:

- **Browser modules:** `tests/js/*.test.mjs` and `tests/web/*.test.mjs` with `node --test` (Node 20 or later). The tests import `web/` modules directly; none of them needs a browser or ComfyUI.
- **Package:** `tests/test_*.py` and `tests/python/test_*.py` with `unittest`, using ComfyUI's Python because the package needs ComfyUI's dependencies (`jsonschema`). The runner uses `$H3_PYTHON`, then the Windows portable install at `~/ComfyUI/ComfyUI_windows_portable/python_embeded/python.exe`, then `python`. Tests that load ComfyUI on the CPU read `COMFY_ROOT`; the runner defaults it to the portable install's `ComfyUI` folder.

To run one Python file, use discovery from the checkout root. ComfyUI's embedded Python does not put the working directory on `sys.path`, so `python -m unittest tests.name` fails there:

```sh
python -m unittest discover -s tests -t . -p test_shot_split_server.py -v
```

`test_skill_pack.py` checks that the instruction bundle serves every skill in `skills/` exactly, entry first, and that `skills/install.py` links the whole pack.

`test_shot_split_server.py` runs `tests/js/emit_shot_split.mjs` in Node. It checks that the renderer reads a Shot split as a Cut with the guides on the correct shots, and still accepts saved paired endpoint guides and interior guides without Shot markers. It is skipped when Node is not on `PATH`.

These tests run on the CPU and load no models. They do not replace watching a render.

The optional settings/browser smoke also checks native and attached new-generation host actions, the upload guard, stale history, and desktop/mobile Project settings without connecting to ComfyUI:

```sh
uv run --with playwright python tests/browser/new_generation.py
```

It uses an installed Chrome when available (override with `PLAYWRIGHT_CHROMIUM_EXECUTABLE`), otherwise Playwright's Chromium. Screenshots go to `.tmp/`.

Saved stories attachment/transport regression (actual frontend host methods with synthetic storage):

```sh
uv run --with playwright python tests/browser/saved_story_attachment.py
```

This checks managed load/status GETs, exact Timeline content, asset bindings, recovery of previously stripped attachments, failed lookups, in-flight edits, conflict preservation, native imports/forks and connected text controls. It never contacts ComfyUI and does not test a full custom-node workflow import or render.
