// SessionStart hook: silent when ready; tells Claude once per session if `reelkit setup` is still needed.
// Also refreshes the `reelkit` command shim when the plugin folder moved (plugin updates change the path).
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DATA, PY, ROOT, shimText, shimPath } from './paths.mjs';

const root = ROOT;
if (!existsSync(PY)) {
  console.log('reelkit: dependencies are not installed yet. Before building a reel run `reelkit setup` (or /reelkit:setup) once; it takes 3-6 minutes.');
  process.exit(0);
}
try {
  const p = shimPath();
  const want = shimText();
  if (!existsSync(p) || readFileSync(p, 'utf8') !== want) { mkdirSync(path.dirname(p), { recursive: true }); writeFileSync(p, want); }
} catch {}
