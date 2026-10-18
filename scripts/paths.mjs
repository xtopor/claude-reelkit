// Where things live. The plugin folder is replaced on updates, so everything heavy (python venv, node modules,
// sound bank, compiled models) lives in a data folder that survives:
//   REELKIT_DATA env  |  Windows: %LOCALAPPDATA%\reelkit  |  else: ~/.local/share/reelkit
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const WIN = process.platform === 'win32';
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const DATA = process.env.REELKIT_DATA
  || (WIN ? path.join(process.env.LOCALAPPDATA || os.homedir(), 'reelkit') : path.join(os.homedir(), '.local', 'share', 'reelkit'));
export const VENV = path.join(DATA, 'venv');
export const PY = path.join(VENV, WIN ? 'Scripts' : 'bin', WIN ? 'python.exe' : 'python');
export const NODE_DIR = path.join(DATA, 'node');
export const NODE_MODULES = path.join(NODE_DIR, 'node_modules');
export const SFX_DIR = path.join(DATA, 'sfx');
export const BIN_DIR = WIN ? path.join(DATA, 'bin') : path.join(os.homedir(), '.local', 'bin');

export function shimPath() { return path.join(BIN_DIR, WIN ? 'reelkit.cmd' : 'reelkit'); }
export function shimText() {
  const cli = path.join(ROOT, 'bin', 'reelkit.mjs');
  return WIN
    ? `@echo off\r\nnode "${cli}" %*\r\n`
    : `#!/usr/bin/env bash\nexec node "${cli}" "$@"\n`;
}

/** Environment for child processes: lets every script find the repo, the data folder and the node modules. */
export function childEnv(extra = {}) {
  return { ...process.env, REELKIT_ROOT: ROOT, REELKIT_DATA: DATA, NODE_PATH: NODE_MODULES, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1', ...extra };
}
