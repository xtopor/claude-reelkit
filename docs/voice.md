# Voice-over

Three options, all giving the engine a `vo/vo.mp3` plus word timings.

## 1. Free TTS (default): Microsoft neural voices via edge-tts
```bash
reelkit voices uk                      # list voices for a language (uk, en, ru, pl, de, …)
reelkit tts reels/my-reel              # script from reel.json → vo/vo.mp3 + vo/vo.words.json
reelkit tts reels/my-reel --voice uk-UA-PolinaNeural --rate +8%
```
- Ukrainian: `uk-UA-OstapNeural` (male, calm storyteller), `uk-UA-PolinaNeural` (female). English: `en-US-AndrewMultilingualNeural`, `en-US-AvaMultilingualNeural`. 70+ languages.
- Word timings come straight from the voice service, so subtitles are exact and Whisper is not needed.
- In the script, `{shown|said}` shows one thing in subtitles and says another: `{99 ₴|дев'яносто дев'ять гривень}`, `{BlackSea|Блек Сі}`. Digits are read correctly in most languages; abbreviations and English brand names inside a Ukrainian text usually need the phonetic form.
- No SSML pauses: a longer pause is made by splitting the script into sentences with a full stop, or with `vo.gaps` in reel.json.
- ~150 words ≈ 60 s. `--rate +5%…+10%` tightens without chipmunk sound.
- **Licence note**: edge-tts (LGPL) talks to Microsoft's free online voice service without an official commercial licence; for business accounts that want a clean paper trail, the same voices are available officially through Azure Speech (free tier 0.5 M characters/month), and the Python code is nearly identical. Decide once per account.

## 2. Your own voice
Record the approved script on your phone, drop it as `vo/vo.mp3` (any format ffmpeg reads). Set `"lang"` in reel.json; faster-whisper (small, CPU) transcribes it for word timings. For talking-to-camera videos use the `talking-head-edit` skill instead — it cleans the audio and cuts fillers.

## 3. ElevenLabs (optional, paid plans for commercial use)
- Pick a voice in your language from the ElevenLabs library (multilingual models handle Ukrainian, Polish, Spanish …). Write numbers as words and brand names phonetically in the TTS text; keep digits and real spelling in `script` for subtitles.
- Free plan: library voices work in the web UI but not via API — generate in the web Text-to-Speech page, then pull the takes:
  ```bash
  export ELEVENLABS_API_KEY=…            # or put ELEVENLABS_API_KEY=… in ~/.config/reelkit/.env
  reelkit voice reels/my-reel 2          # saves the 2 newest takes to vo/ and prints durations
  ```
  The key needs the *speech history read* permission. Transcribe both (`reelkit build … --stills` does it for `vo/vo.mp3`) and keep the cleaner one.
- **Rights**: the ElevenLabs free plan does not grant commercial use and requires attribution. For reels that sell something, use a paid plan, the free Microsoft voices, or your own voice.
