// claude-reelkit setup: python venv (numpy, faster-whisper, opencv, edge-tts, rembg), Playwright Chromium in the
// data folder, the synthesised sound bank, and the `reelkit` command on your PATH. Re-run any time; `--check` only reports.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync, readFileSync, chmodSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { ROOT, DATA, VENV, PY, NODE_DIR, NODE_MODULES, SFX_DIR, BIN_DIR, WIN, shimPath, shimText, childEnv } from './paths.mjs';

const CHECK = process.argv.includes('--check');
let missing = 0;
const ok = m => console.log(`  \x1b[32m✓\x1b[0m ${m}`);
const bad = m => { console.log(`  \x1b[31m✗\x1b[0m ${m}`); missing++; };
const note = m => console.log(`  · ${m}`);
const env = childEnv();

function which(bin, flag = '--version') {
  const r = spawnSync(bin, [flag], { encoding: 'utf8', env, shell: false });
  return r.status === 0 ? (r.stdout || r.stderr || '').split('\n')[0].trim() : null;
}
function sh(bin, args, opts = {}) {
  const r = spawnSync(bin, args, { stdio: opts.quiet ? 'pipe' : 'inherit', env: { ...env, ...(opts.env || {}) }, cwd: opts.cwd, shell: !!opts.shell, encoding: 'utf8' });
  if (r.error) throw new Error(`${bin}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${bin} ${args.join(' ')} failed${opts.quiet ? ':\n' + (r.stderr || r.stdout) : ''}`);
  return r.stdout;
}
/** npm without a shell: Windows cannot spawn npm.cmd directly, so run npm's own JS entry with this node. */
function npm(args, opts = {}) {
  const cli = path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js');
  if (existsSync(cli)) return sh(process.execPath, [cli, ...args], opts);
  return sh(WIN ? 'npm.cmd' : 'npm', args, { ...opts, shell: WIN });
}
const onPath = dir => (process.env.PATH || '').split(path.delimiter).map(p => p.toLowerCase().replace(/[\\/]+$/, '')).includes(dir.toLowerCase().replace(/[\\/]+$/, ''));
/** The system python that can make a venv: python3, python, or the Windows launcher. */
function sysPython() {
  for (const c of [['python3', []], ['python', []], ['py', ['-3']]]) {
    const r = spawnSync(c[0], [...c[1], '-c', 'import sys;print(sys.version_info[0]*100+sys.version_info[1])'], { encoding: 'utf8', shell: false });
    if (r.status === 0 && +r.stdout.trim() >= 310) return c;
  }
  return null;
}

console.log(`claude-reelkit · ${ROOT}\n  data: ${DATA}`);
console.log('System tools:');
for (const t of ['ffmpeg', 'ffprobe']) which(t, '-version') ? ok(t) : bad(`${t} (Windows: winget install Gyan.FFmpeg · macOS: brew install ffmpeg · Linux: apt install ffmpeg)`);
const nv = +process.versions.node.split('.')[0];
nv >= 20 ? ok(`node ${process.versions.node}`) : bad(`node >= 20 needed (have ${process.versions.node})`);
existsSync(path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js')) || which('npm') ? ok('npm') : bad('npm');
const spy = sysPython();
spy ? ok(`python (${spy[0]} ${spy[1].join(' ')})`.trim()) : bad('python >= 3.10 (Windows: winget install Python.Python.3.12 · macOS: brew install python)');

if (CHECK) {
  console.log('Project:');
  existsSync(PY) ? ok(`python venv (${VENV})`) : bad('python venv (run: reelkit setup)');
  if (existsSync(PY)) {
    const r = spawnSync(PY, ['-I', '-c', 'import faster_whisper, edge_tts, rembg, cv2, numpy; print("ok")'], { encoding: 'utf8', env });
    r.status === 0 ? ok('faster-whisper, edge-tts, rembg, opencv') : bad('python packages incomplete (run: reelkit setup)');
  }
  existsSync(path.join(NODE_MODULES, 'playwright')) ? ok('playwright') : bad('playwright (run: reelkit setup)');
  if (existsSync(path.join(NODE_MODULES, 'playwright'))) {
    const r = spawnSync(process.execPath, ['-e', 'const {chromium}=require("playwright");const p=chromium.executablePath();require("fs").existsSync(p)?console.log(p):process.exit(1)'], { encoding: 'utf8', env, cwd: NODE_DIR });
    r.status === 0 ? ok('chromium') : bad('chromium (run: reelkit setup)');
  }
  existsSync(path.join(SFX_DIR, 'whoosh.wav')) ? ok('sound bank') : bad('sound bank (run: reelkit setup)');
  onPath(BIN_DIR) && existsSync(shimPath()) ? ok('reelkit on PATH') : bad(`reelkit not on PATH (${WIN ? 'restart the terminal, or add ' + BIN_DIR + ' to PATH' : 'add ~/.local/bin to PATH'})`);
  process.env.ELEVENLABS_API_KEY || existsSync(path.join(os.homedir(), '.config', 'reelkit', '.env')) ? ok('ElevenLabs key') : note('ElevenLabs key: optional, the free Microsoft voices work without it (docs/voice.md)');
  existsSync(process.env.CAPCUT_PLUGIN_DIR || path.join(os.homedir(), 'capcut-plugin')) ? ok('CapCut plugin bundle') : note('CapCut plugin bundle: optional, see docs/capcut.md');
  process.exit(missing ? 1 : 0);
}
if (missing) { console.log('Install the missing tools above, then run this again.'); process.exit(1); }

try {
  console.log('Python venv:');
  mkdirSync(DATA, { recursive: true });
  if (!existsSync(PY)) sh(spy[0], [...spy[1], '-m', 'venv', VENV]);
  sh(PY, ['-m', 'pip', 'install', '-q', '--upgrade', 'pip'], { quiet: true });
  sh(PY, ['-m', 'pip', 'install', '-q', '-r', path.join(ROOT, 'requirements.txt')]);
  ok(`numpy, faster-whisper, opencv, edge-tts, rembg → ${VENV}`);
  try { sh(PY, ['-m', 'pip', 'install', '-q', 'pillow-heif'], { quiet: true }); ok('pillow-heif (HEIC photos)'); } catch { note('pillow-heif not installed (HEIC photos will go through ffmpeg)'); }

  console.log('Node + Chromium:');
  mkdirSync(NODE_DIR, { recursive: true });
  const pkg = path.join(NODE_DIR, 'package.json');
  if (!existsSync(pkg)) writeFileSync(pkg, JSON.stringify({ name: 'reelkit-runtime', private: true, dependencies: { playwright: '1.56.1' } }, null, 2));
  if (!existsSync(path.join(NODE_MODULES, 'playwright'))) npm(['install', '--silent', '--no-audit', '--no-fund'], { cwd: NODE_DIR });
  ok('playwright');
  sh(process.execPath, [path.join(NODE_MODULES, 'playwright', 'cli.js'), 'install', 'chromium'], { cwd: NODE_DIR });
  ok('chromium');

  console.log('Sound bank:');
  mkdirSync(SFX_DIR, { recursive: true });
  sh(PY, ['-I', path.join(ROOT, 'engine', 'sfx.py'), SFX_DIR], { quiet: true });
  ok(`${SFX_DIR}`);

  console.log('Models (first download, cached):');
  try { sh(PY, ['-I', '-c', 'from faster_whisper import WhisperModel; WhisperModel("small", device="cpu", compute_type="int8")'], { quiet: true }); ok('faster-whisper small'); }
  catch { note('faster-whisper model will download on first build (needs huggingface.co)'); }
  try { sh(PY, ['-I', '-c', 'from rembg import new_session; new_session("u2net_human_seg")'], { quiet: true }); ok('rembg u2net_human_seg (person masks)'); }
  catch { note('rembg model will download on first use of cover / orbit (needs github.com)'); }

  console.log('Command:');
  mkdirSync(BIN_DIR, { recursive: true });
  const shim = shimPath(); writeFileSync(shim, shimText()); if (!WIN) chmodSync(shim, 0o755);
  ok(`reelkit → ${shim}`);
  if (WIN) {
    const cur = (spawnSync('reg', ['query', 'HKCU\\Environment', '/v', 'Path'], { encoding: 'utf8' }).stdout || '');
    const m = cur.match(/Path\s+REG_(?:EXPAND_)?SZ\s+(.*)/i); const userPath = m ? m[1].trim() : '';
    if (!userPath.toLowerCase().split(';').includes(BIN_DIR.toLowerCase())) {
      const r = spawnSync('powershell', ['-NoProfile', '-Command', `[Environment]::SetEnvironmentVariable('Path', ([Environment]::GetEnvironmentVariable('Path','User').TrimEnd(';') + ';${BIN_DIR}'), 'User')`], { encoding: 'utf8' });
      r.status === 0 ? note(`added ${BIN_DIR} to your user PATH — open a new terminal for "reelkit" to work there`) : note(`add ${BIN_DIR} to your PATH by hand`);
    }
  } else if (!onPath(BIN_DIR)) note(`add to your shell profile: export PATH="$HOME/.local/bin:$PATH"`);
  console.log('Done. Next: open Claude Code and say "make a reel from my clips".');
} catch (e) {
  console.error(`\nsetup failed: ${e.message}`); process.exit(1);
}
