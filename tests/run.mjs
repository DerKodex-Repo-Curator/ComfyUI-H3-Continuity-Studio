// Runs the browser-module tests (node --test) and the package tests (unittest) with ComfyUI's Python.
// Python: $H3_PYTHON, else the Windows portable ComfyUI Python if present, else `python`.
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const portable = join(homedir(), 'ComfyUI', 'ComfyUI_windows_portable', 'python_embeded', 'python.exe');
const python = process.env.H3_PYTHON || (existsSync(portable) ? portable : 'python');
const run = (command, args) => spawnSync(command, args, { cwd: root, stdio: 'inherit' }).status;

const js = run(process.execPath, ['--test', 'tests/js/*.test.mjs']);
// `discover -t .` puts the checkout on sys.path, which ComfyUI's embedded Python does not do for `-m`.
const py = run(python, ['-m', 'unittest', 'discover', '-s', 'tests', '-t', '.', '-p', 'test_*.py']);
if (py == null) console.error(`Could not start ${python}; set H3_PYTHON to ComfyUI's Python.`);
process.exit(js === 0 && py === 0 ? 0 : 1);
