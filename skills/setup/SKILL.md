---
name: setup
description: Install everything reelkit needs (python venv with faster-whisper, edge-tts, rembg; Playwright Chromium; the synthesised sound bank; the `reelkit` command on PATH). Use when the user runs /reelkit:setup, asks to "set up reelkit", "install the reel tools", "установи reelkit", or when `reelkit doctor` reports something missing.
disable-model-invocation: true
allowed-tools: Bash(node *), Bash(reelkit *)
---

Run the setup script and show the user what it printed, in their language, in plain words:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.mjs"
```

It takes 3–6 minutes the first time (downloads Chromium ~150 MB, the Whisper "small" model ~250 MB and the rembg person model ~170 MB). Re-running is safe and fast.

If it reports missing system tools, tell the user the one-line install for their OS (printed next to the ✗) and stop. ffmpeg, node ≥ 20 and python ≥ 3.10 must already be installed; the script does not install them.

On Windows the script adds `%LOCALAPPDATA%\reelkit\bin` to the user PATH: the `reelkit` command works in new terminals. In the current session use `node "${CLAUDE_PLUGIN_ROOT}/bin/reelkit.mjs" …` if `reelkit` is not found yet.

When it ends with "Done", run `node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.mjs" --check` and confirm every line is ✓.
