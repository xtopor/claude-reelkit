// Renders the reel page frame by frame with Playwright Chromium (installed by `reelkit setup` into the data folder).
//   node tools/render.mjs <reel-dir> stills <t1,t2,...>          -> <reel-dir>/stills/t_<t>.jpg
//   node tools/render.mjs <reel-dir> video <out.mp4> [fps]       -> MP4 (silent, x264 crf 18)
// Env: W, H (viewport), PAGE (index.html?nosubs=1), CHROME (own Chrome/Chromium executable), REELKIT_FFMPEG.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { DATA, NODE_DIR } from '../scripts/paths.mjs';

const require = createRequire(path.join(NODE_DIR, 'package.json'));
const { chromium } = require('playwright');
const [dir, mode, out, fpsArg] = process.argv.slice(2);
const fps = +(fpsArg || 30);
const ffmpeg = process.env.REELKIT_FFMPEG || 'ffmpeg';
const browser = await chromium.launch({ ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}), args: ['--force-color-profile=srgb', '--disable-gpu-vsync'] });
const page = await browser.newPage({ viewport: { width: +(process.env.W || 1920), height: +(process.env.H || 1080) }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('PAGEERR', e.message));
page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
const [pageFile, query] = (process.env.PAGE || 'index.html').split('?');
await page.goto(pathToFileURL(path.join(path.resolve(dir), pageFile)).href + (query ? '?' + query : ''));
await page.evaluate(() => window.ready);
await page.waitForTimeout(300);
if (mode === 'stills') {
  const times = out.split(',').map(Number);
  for (const t of times) {
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: path.join(dir, 'stills', `t_${t.toFixed(2)}.jpg`), type: 'jpeg', quality: 80 });
  }
} else {
  const dur = await page.evaluate(() => window.DUR);
  const n = Math.round(dur * fps);
  const ff = spawn(ffmpeg, ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  ff.on('error', e => { console.error('ffmpeg:', e.message); process.exit(1); });
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.render(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
}
await browser.close();
