// Renders edit.json frame by frame with Playwright Chromium (installed by `reelkit setup` into the data folder),
// then muxes the frames with the original audio through ffmpeg.
//   reelkit th render edit.json out.mp4            -> MP4 (x264 crf 18 + aac)
//   AT=0.5,3,6 reelkit th render edit.json out.mp4 -> PNG stills in frames/ next to edit.json
// Env: CHROME_PATH (own Chrome/Chromium executable), REELKIT_FFMPEG (ffmpeg executable, default "ffmpeg").
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { NODE_DIR } from '../../../scripts/paths.mjs';

const [edlPath, outPath] = process.argv.slice(2);
if (!edlPath || !outPath) { console.error('usage: node render.mjs edit.json out.mp4  [AT=1.5,3 for stills]'); process.exit(1); }

// playwright lives in the data folder, not next to this file: resolve it from there (same as tools/render.mjs)
let chromium;
try { ({ chromium } = createRequire(path.join(NODE_DIR, 'package.json'))('playwright')); }
catch (e) { console.error(`playwright not found in ${NODE_DIR} (${e.message}). Run: reelkit setup`); process.exit(1); }

const ffmpeg = process.env.REELKIT_FFMPEG || 'ffmpeg';
const engineDir = path.dirname(fileURLToPath(import.meta.url));
const edlFile = path.resolve(edlPath);
const workDir = path.dirname(edlFile);
const edl = JSON.parse(fs.readFileSync(edlFile, 'utf8'));
const fps = edl.fps || 30;
const framesDir = path.join(workDir, 'frames');
fs.rmSync(framesDir, { recursive: true, force: true });
fs.mkdirSync(framesDir, { recursive: true });

// Tiny static server: "/" is the template, everything else is a file next to edit.json (range requests for <video>).
const types = { '.html': 'text/html', '.webm': 'video/webm', '.mp4': 'video/mp4', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.woff2': 'font/woff2', '.ttf': 'font/ttf' };
const inside = (p, root) => { const r = path.relative(root, p); return r !== '' && !r.startsWith('..') && !path.isAbsolute(r); };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const p = u === '/' ? path.join(engineDir, 'template.html') : path.resolve(workDir, '.' + u);
  if (!(inside(p, workDir) || inside(p, engineDir)) || !fs.existsSync(p) || !fs.statSync(p).isFile()) { res.writeHead(404); res.end(); return; }
  const size = fs.statSync(p).size, range = req.headers.range;
  const ct = types[path.extname(p).toLowerCase()] || 'application/octet-stream';
  if (range) {
    const [a, b] = range.replace('bytes=', '').split('-');
    const start = +a, end = b ? +b : size - 1;
    res.writeHead(206, { 'content-type': ct, 'accept-ranges': 'bytes', 'content-range': `bytes ${start}-${end}/${size}`, 'content-length': end - start + 1 });
    fs.createReadStream(p, { start, end }).pipe(res);
  } else { res.writeHead(200, { 'content-type': ct, 'accept-ranges': 'bytes', 'content-length': size }); fs.createReadStream(p).pipe(res); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));

const browser = await chromium.launch({
  ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}),
  args: ['--autoplay-policy=no-user-gesture-required', '--force-color-profile=srgb'],
});
const page = await browser.newPage({ viewport: { width: edl.width, height: edl.height }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.log('pageerror:', e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/`);
await page.evaluate(e => window.setup(e), edl);

const only = process.env.AT ? process.env.AT.split(',').map(Number) : null;
const times = only || Array.from({ length: Math.round(edl.duration * fps) }, (_, i) => i / fps);
const t0 = Date.now();
for (let i = 0; i < times.length; i++) {
  await page.evaluate(t => window.renderAt(t), times[i]);
  const name = only ? `still_${times[i].toFixed(2)}.png` : `f_${String(i).padStart(5, '0')}.jpg`;
  await page.screenshot(only ? { path: path.join(framesDir, name), type: 'png' } : { path: path.join(framesDir, name), type: 'jpeg', quality: 92 });
  if (i % 60 === 0) console.log(`frame ${i}/${times.length} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
await browser.close();
server.close();
if (only) { console.log('stills in', framesDir); process.exit(0); }

const args = ['-v', 'error', '-y', '-framerate', String(fps), '-i', path.join(framesDir, 'f_%05d.jpg')];
if (edl.audio) args.push('-ss', String(edl.sourceOffset || 0), '-i', path.resolve(workDir, edl.audio), '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest');
args.push('-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', path.resolve(outPath));
try { execFileSync(ffmpeg, args, { stdio: 'inherit' }); }
catch (e) { console.error(`ffmpeg failed (${ffmpeg}): ${e.message}`); process.exit(1); }
console.log('wrote', path.resolve(outPath));
