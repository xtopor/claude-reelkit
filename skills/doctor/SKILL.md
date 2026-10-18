---
name: doctor
description: Check that reelkit is fully installed (ffmpeg, node, python venv packages, Chromium, sound bank, the command on PATH, optional keys). Use when the user runs /reelkit:doctor, asks "is reelkit ready?", "проверь, всё ли установлено для рилсов", or before the first build in a session.
disable-model-invocation: true
allowed-tools: Bash(node *), Bash(reelkit *)
---

Run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.mjs" --check
```

Report the ✗ lines in the user's language with the fix printed next to each. If only "python venv / playwright / sound bank" are missing, offer to run `/reelkit:setup`. Lines marked "·" are optional (ElevenLabs, CapCut) and not a problem.
