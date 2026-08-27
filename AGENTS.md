# Agent notes

Keep the repo root as scripts + config only. Every episode lives in its own folder under `uploads/`.

Cursor loads this file automatically (project-root `AGENTS.md`). There is also `.cursor/rules/uploads-layout.mdc` (`alwaysApply: true`). Prefer this file as the source of truth.

## Layout

```
.
├── create_video.py              # audio + cover → MP4
├── translate_to_marathi.py      # Gujarati audio → Marathi text + speech
├── src/                         # library code (do not dump media here)
│   ├── job.py                   # resolves a job folder or audio file
│   ├── transcribe.py
│   ├── cover_art.py
│   ├── video.py
│   ├── main.py
│   └── prompt_loader.py
├── prompts/                     # cover-art style prompts
├── .env                         # API keys (never commit)
├── uploads/                     # ALL generated / episode files
│   └── <episode-name>/
│       ├── source/              # source audio, transcripts, research
│       ├── drafts/              # reviewable work, grouped by type
│       ├── previews/            # short audio/video quality checks
│       ├── logs/                # generation logs
│       ├── .podcast/            # caches and intermediate working files
│       ├── podcast.json         # active podcast config, when applicable
│       ├── <slug>.png           # approved canonical cover
│       ├── <slug>.podcast.mp3   # final mastered audio
│       ├── <slug>_video.mp4     # final video
│       └── <slug>.youtube.md    # final upload package
└── AGENTS.md
```

Do not write audio, video, transcripts, or cover art to the repo root, `src/`, or a shared `data/` dump.

## New upload

1. Create `uploads/<episode-name>/`.
2. Put the source `.m4a` (and optional cover PNG) in that folder.
3. Run scripts against the **folder**:

```bash
source ~/pyenv/notebooklm-to-video/bin/activate
python3 create_video.py uploads/<episode-name> --auto-approve
python3 create_video.py uploads/<episode-name> --cover-art uploads/<episode-name>/cover.png --auto-approve
python3 translate_to_marathi.py uploads/<episode-name>
```

`src/job.py` accepts a folder or an audio file inside it. If audio is dropped on the repo root and a script is run, it is moved into `uploads/<stem>/`. Prefer creating the folder first.

## Environment

- Keys: repo-root `.env` (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`). Never commit it.
- Python: `~/pyenv/notebooklm-to-video` via `uv` (Python 3.12). Deps: `python-dotenv`, `requests`.
- ffmpeg: required (`/opt/homebrew/bin/ffmpeg`).
- whisper.cpp: `~/LLM-apps/whisper.cpp/build/bin/whisper-cli`.
- Long-running jobs (whisper, Gemini audio, TTS, ffmpeg encode): run in tmux. Do not pipe through `tail` — it hides progress until the process exits.

## Video (`create_video.py` / `src/video.py`)

- Main CLI is `create_video.py`, not `src/main.py`, unless the user wants the interactive prompt.
- `--cover-art` skips transcription. Use this when a PNG already exists or you will drive art from a custom prompt.
- `--prompt` only overrides cover-art *content*. It does **not** skip transcription. For non-English audio, pass `--cover-art` or generate art separately, then encode with `--cover-art`.
- ffmpeg must use `-y` (overwrite). Without it, encode hangs forever waiting for an interactive `Overwrite? [y/N]`.
- Still-image flags already in `src/video.py`: `-tune stillimage -pix_fmt yuv420p -r 2`. Keep them; a 20-min default-fps encode is slow and huge.
- Output is `{stem}_video.mp4` in the job folder. Square covers produce square video (letterboxed on YouTube). Pad to 1920×1080 only if the user asks.

## Cover art (`src/cover_art.py`)

- OpenRouter model: `google/gemini-3-pro-image-preview`. Image gen is fast (~20s). Whisper on ~20 min audio is the slow step (~6 min).
- `get_image_prompt()` only uses the first ~400 characters of the transcript. For themed art, pass a tight custom prompt.
- User prefers **content-accurate** art (named people/places/concepts from the episode) over generic “weird” symbolism (glowing brains, puzzle eyes).
- If the user supplies a PNG, use `--cover-art` and copy it into the job folder. Do not regenerate unless they ask.

## Language / transcription

- Installed whisper model `ggml-tiny.en.bin` is **English-only**. Gujarati/Marathi audio produces garbage (`(speaking in foreign language)`, stuck loops like “The nuclear question”).
- Do not use `tiny.en` (or VoiceInk English STT) as a source of truth for Indic audio.
- For real Gujarati transcripts: multilingual whisper (`medium`/`large`, `--language gu`) **or** Gemini audio-input (`google/gemini-3.1-pro-preview`) via OpenRouter chat completions with `input_audio`.
- Gujarati→Marathi **text** translation is strong. The weak links are Gujarati STT and Marathi TTS, not the translation hop.

## Gujarati → Marathi (`translate_to_marathi.py`)

Preferred pipeline (Option B, not separate STT then translate):

1. Chunk audio (~300s, mono 16 kHz mp3).
2. `google/gemini-3.1-pro-preview` hears the chunk and returns Gujarati transcript **and** Marathi translation in one call.
3. TTS: `google/gemini-3.1-flash-tts-preview`, voice `Kore`.
4. Gemini TTS accepts **`response_format: "pcm"` only** (24 kHz s16le mono). Wrap with ffmpeg to mp3. `mp3` on that endpoint returns 400.
5. Split Marathi text into ~1200-char TTS chunks, concatenate PCM, then encode.

Outputs in the job folder: `<stem>.gujarati.txt`, `<stem>.marathi.txt`, `<stem>.marathi.mp3`.

TTS is a single narrator. Source audio is often a two-host podcast; distinct voices only if the user asks.

OpenRouter has no true Gujarati-speech→Marathi-speech model. There is always text in the middle.

## YouTube package (when asked)

- Title: curiosity-gap in the spoken language + English search keywords (`Free Private Cities`, episode topic).
- Description: what/why, chapter list starting at `00:00` (YouTube auto-chapters), sources, disclaimer, 3–5 hashtags.
- Thumbnail: the cover PNG in the job folder.
- Settings: language matches audio, category Education, not made for kids, Unlisted first then Public.
- Virality extras only if asked: pin a poll comment, cut 2–3 Shorts from the strongest hooks.

## OpenRouter

- Docs: MCP `user-openrouter.ai` `searchDocs`, or `https://openrouter.ai/docs`.
- Discover models: `GET /api/v1/models?input_modalities=audio` and `?output_modalities=speech|transcription`.
- Audio-input chat (`/chat/completions` + `input_audio`) is for translate/analyze. Dedicated STT (`/audio/transcriptions`) is for plain transcripts.
- TTS: `POST /api/v1/audio/speech`. Check each model’s format/voice constraints (Gemini = PCM only).

## Script to podcast (`create_podcast.py`)

The script-to-podcast pipeline uses this episode-local layout:

```text
uploads/
└── <episode-name>/
    ├── source/
    │   ├── <source-audio>.m4a
    │   ├── transcript.txt
    │   └── <research>.md
    ├── drafts/
    │   └── cover-art/
    │       ├── cover-art-intent.md
    │       ├── cover-art-prompts.md
    │       └── <candidate>.png
    ├── previews/
    │   └── audio/
    │       └── <preview>.mp3
    ├── logs/
    │   └── <generation>.log
    ├── podcast.json
    ├── .podcast/
    │   ├── manifest.json
    │   ├── segments/             # OpenRouter per-turn cache
    │   ├── native-chunks/        # native Gemini multi-speaker cache
    │   └── intermediates/
    │       └── <slug>.podcast.wav
    ├── <slug>.podcast.mp3
    ├── <slug>.png
    ├── <slug>_video.mp4
    └── <slug>.youtube.md
```

Keep the episode root clean: only `podcast.json` and approved canonical deliverables belong there. Put source material, drafts, previews, logs, caches, and intermediate WAV files in their named subdirectories. These files do not weaken the upload-folder rule: every artifact must remain inside the selected `uploads/<episode-name>/` folder. Do not write podcast artifacts to the repo root, `src/`, or `data/`.

Image generators may initially save output in Cursor's generated-assets area. Copy each candidate immediately to `drafts/cover-art/` with a descriptive filename. Do not replace `<slug>.png` until the user approves a candidate. After approval, copy it to the canonical name and re-encode only the video; never regenerate approved audio just to change cover art.

After final approval, remove rejected drafts, quality-test previews, generation logs, obsolete backend caches, and preview WAV files. Retain only reproducibility inputs in `source/`, `podcast.json`, the approved canonical deliverables, the cache used for the final render, and the final mastering WAV under `.podcast/intermediates/`.

Run the pipeline against the episode folder:

```bash
source ~/pyenv/notebooklm-to-video/bin/activate
python3 create_podcast.py uploads/<episode-name> --auto-approve
python3 create_podcast.py uploads/<episode-name> --cover-art uploads/<episode-name>/cover.png --auto-approve
python3 create_podcast.py uploads/<episode-name> --force-audio --force-art --auto-approve
```

OpenRouter TTS renders one configured speaker voice per request. This can cause voice-identity drift across independently rendered turns. For a two-speaker podcast where identity consistency matters, prefer native Gemini multi-speaker TTS with `GEMINI_API_KEY`, render chapter-aligned chunks, and cache them in `.podcast/native-chunks/`. English inline tags such as `[laughs]` and `[whispers]` may be used in turn text. `.podcast/segments/` caches OpenRouter turn renders; `--force-audio` regenerates them. `<slug>.youtube.md` and the media assets support manual YouTube upload only. Long paid generation and ffmpeg runs must be launched in tmux.
