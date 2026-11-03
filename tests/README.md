# Tests

```sh
node tests/run.mjs
```

This runs two suites:

- **Browser modules:** `tests/js/*.test.mjs` with `node --test` (Node 20 or later). The tests import `web/` modules directly; none of them needs a browser or ComfyUI.
- **Package:** `tests/test_*.py` with `unittest`, using ComfyUI's Python because the package needs ComfyUI's dependencies (`jsonschema`). The runner uses `$H3_PYTHON`, then the Windows portable install at `~/ComfyUI/ComfyUI_windows_portable/python_embeded/python.exe`, then `python`.

To run one Python file, use discovery from the checkout root. ComfyUI's embedded Python does not put the working directory on `sys.path`, so `python -m unittest tests.name` fails there:

```sh
python -m unittest discover -s tests -t . -p test_guide_split_server.py -v
```

`test_guide_split_server.py` runs `tests/js/emit_guide_split.mjs` in Node. It checks that the render code reads the browser's split of a clip in the way the browser intends. It is skipped when Node is not on `PATH`.

These tests run on the CPU and load no models. They do not replace watching a render.
