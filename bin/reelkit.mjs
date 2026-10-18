#!/usr/bin/env node
// reelkit — one entry point for the reel engine, so skills never need to know where the plugin lives.
// Cross-platform (Windows, Linux, macOS). Heavy dependencies live in the data folder (see scripts/paths.mjs).
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { ROOT, DATA, PY, WIN, childEnv } from '../scripts/paths.mjs';

const usage = `reelkit — reels from your own footage (Claude Code plugin)

  reelkit setup                     install dependencies (python venv, Playwright Chromium, sound bank, the command)
  reelkit doctor                    check that everything is in place
  reelkit new <reel-dir>            start a reel folder from the template
  reelkit sheet <clip>... [-o dir]  contact sheets (10 frames per clip) to pick moments
  reelkit voices [lang]             list free TTS voices (edge-tts), e.g. "reelkit voices uk"
  reelkit tts <reel-dir> [--voice NAME] [--rate +5%] [--pitch +0Hz] [--text "..."]
                                    voice-over from reel.json "script" (free Microsoft voices) -> vo/vo.mp3 + vo/words.json
  reelkit voice <reel-dir> [n]      pull the n newest ElevenLabs takes into <reel-dir>/vo/ (optional, needs API key)
  reelkit build <reel-dir> [--stills] [--capcut]
                                    render the reel (--stills = fast preview + safe-zone QA sheet)
  reelkit stills <reel-dir> <t1,t2,...>
                                    render single frames at those times into <reel-dir>/stills/
  reelkit masks <frames-dir> <out-dir>
                                    person masks (rembg, alpha PNG) + head positions, for cover / orbit
  reelkit sfx                       (re)generate the synthesised sound bank in the data folder
  reelkit capcut stems|draft <reel-dir>
                                    stems + CapCut draft JSON with sound effects (see docs/capcut.md)
  reelkit th <lines|tighten|cut|qa|clean|transcribe|render> [args]
                                    talking-head tools (skills/talking-head-edit)
  reelkit root | py | data          print the plugin root / the venv python / the data folder
`;

const [cmd = 'help', ...args] = process.argv.slice(2);
const env = childEnv();

function run(bin, a, opts = {}) {
  const r = spawnSync(bin, a.map(String), { stdio: 'inherit', env, shell: false, ...opts });
  if (r.error) { console.error(`reelkit: cannot run ${bin}: ${r.error.message}`); process.exit(1); }
  process.exit(r.status ?? 1);
}
function py(script, a = []) {
  if (!existsSync(PY)) { console.error('reelkit: not set up yet, run: reelkit setup'); process.exit(1); }
  run(PY, ['-I', '-X', 'utf8', script, ...a]);   // -I ignores PYTHON* env vars, so UTF-8 mode goes on the command line
}
const node = WIN ? 'node.exe' : 'node';
const TH = path.join(ROOT, 'skills', 'talking-head-edit');

switch (cmd) {
  case 'root': console.log(ROOT); break;
  case 'py': console.log(PY); break;
  case 'data': console.log(DATA); break;
  case 'setup': run(node, [path.join(ROOT, 'scripts', 'setup.mjs'), ...args]); break;
  case 'doctor': run(node, [path.join(ROOT, 'scripts', 'setup.mjs'), '--check', ...args]); break;
  case 'new': {
    const dir = args[0]; if (!dir) { console.error('usage: reelkit new <reel-dir>'); process.exit(1); }
    for (const d of ['src', 'vo']) mkdirSync(path.join(dir, d), { recursive: true });
    const spec = path.join(dir, 'reel.json');
    if (!existsSync(spec)) copyFileSync(path.join(ROOT, 'examples', 'template', 'reel.json'), spec);
    console.log(`created ${dir} (put clips in ${path.join(dir, 'src')}, voice in ${path.join(dir, 'vo', 'vo.mp3')} or run "reelkit tts ${dir}", edit ${spec})`);
    break;
  }
  case 'sheet': py(path.join(ROOT, 'tools', 'contact_sheet.py'), args); break;
  case 'voices': py(path.join(ROOT, 'engine', 'tts.py'), ['--list', ...args]); break;
  case 'tts': py(path.join(ROOT, 'engine', 'tts.py'), args); break;
  case 'voice': py(path.join(ROOT, 'engine', 'pull_vo.py'), args); break;
  case 'build': py(path.join(ROOT, 'engine', 'build.py'), args); break;
  case 'stills': {
    const dir = path.resolve(args[0] || ''); const times = args[1];
    if (!args[0] || !times) { console.error('usage: reelkit stills <reel-dir> <t1,t2,...>'); process.exit(1); }
    mkdirSync(path.join(dir, 'stills'), { recursive: true });
    run(node, [path.join(ROOT, 'tools', 'render.mjs'), dir, 'stills', times], { env: { ...env, W: '1080', H: '1920' } });
    break;
  }
  case 'masks': py(path.join(ROOT, 'engine', 'masks.py'), args); break;
  case 'sfx': py(path.join(ROOT, 'engine', 'sfx.py'), [path.join(DATA, 'sfx'), ...args]); break;
  case 'capcut': {
    const [sub, dir] = args; if (!sub || !dir) { console.error('usage: reelkit capcut stems|draft <reel-dir>'); process.exit(1); }
    py(path.join(ROOT, 'engine', 'capcut.py'), [dir, sub]); break;
  }
  case 'th': {
    const [sub, ...rest] = args;
    const map = { lines: 'prep/lines.py', tighten: 'prep/tighten.py', cut: 'prep/cut.py', qa: 'prep/qa.py', clean: 'prep/clean_audio.py', transcribe: 'engine/transcribe.py' };
    if (sub === 'render') run(node, [path.join(TH, 'engine', 'render.mjs'), ...rest]);
    else if (map[sub]) py(path.join(TH, map[sub]), rest);
    else { console.error('usage: reelkit th lines|tighten|cut|qa|clean|transcribe|render [args]'); process.exit(1); }
    break;
  }
  case 'help': case '-h': case '--help': console.log(usage); break;
  default: console.error(`unknown command: ${cmd}\n`); console.log(usage); process.exit(1);
}
