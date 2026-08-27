#!/usr/bin/env python3
"""
Gujarati audio -> Marathi audio pipeline (OpenRouter).

Approach (recommended "Option B"):
  1. Split source audio into chunks (compressed mono mp3 to keep payloads small).
  2. Send each chunk to a Gemini audio-input model and ask it to BOTH transcribe
     the Gujarati and translate to natural narration-ready Marathi in one call.
  3. Concatenate the Gujarati transcript and Marathi translation.
  4. Synthesize the Marathi text with Gemini TTS (raw PCM), concatenate, encode mp3.

Outputs (in the job folder, <stem> = input stem):
  <stem>.gujarati.txt
  <stem>.marathi.txt
  <stem>.marathi.mp3
"""

import os
import sys
import time
import base64
import subprocess
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent / "src"))
from job import resolve_job

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE = "https://openrouter.ai/api/v1"

# Models
AUDIO_LLM = "google/gemini-3.1-pro-preview"      # hears Gujarati, writes Gujarati + Marathi
TTS_MODEL = "google/gemini-3.1-flash-tts-preview"  # text -> Marathi speech (PCM only)
TTS_VOICE = "Kore"

CHUNK_SECONDS = 300          # audio chunk length for the audio-LLM
TTS_CHAR_LIMIT = 1200        # max chars per TTS request
TTS_SAMPLE_RATE = 24000      # Gemini TTS PCM output: 24kHz, s16le, mono

DELIM_GU = "===GUJARATI==="
DELIM_MR = "===MARATHI==="

TRANSLATE_PROMPT = f"""You are given an audio segment of a Gujarati audiobook about intelligence analysis, \
cognitive bias, and a 2025 US-Israel-Iran nuclear conflict.

Do two things:
1. Transcribe the Gujarati speech accurately (Gujarati script).
2. Translate it into natural, fluent Marathi suitable for spoken narration (Devanagari). \
Keep meaning faithful; do not summarize or omit content. Keep proper nouns (Iran, FRONTLINE, \
Heuer, ACH) recognizable. Do not add commentary.

Output EXACTLY in this format, nothing else:
{DELIM_GU}
<gujarati transcript here>
{DELIM_MR}
<marathi translation here>
"""


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def split_audio(audio_path: Path, workdir: Path) -> list[Path]:
    pattern = str(workdir / "chunk_%03d.mp3")
    print(f"Splitting audio into {CHUNK_SECONDS}s mono mp3 chunks...")
    run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", "-b:a", "64k",
        "-f", "segment", "-segment_time", str(CHUNK_SECONDS),
        pattern,
    ])
    chunks = sorted(workdir.glob("chunk_*.mp3"))
    print(f"  -> {len(chunks)} chunks")
    return chunks


def transcribe_translate_chunk(chunk: Path, idx: int) -> tuple[str, str]:
    b64 = base64.b64encode(chunk.read_bytes()).decode()
    payload = {
        "model": AUDIO_LLM,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": TRANSLATE_PROMPT},
                {"type": "input_audio", "input_audio": {"data": b64, "format": "mp3"}},
            ],
        }],
        "temperature": 0.2,
    }
    print(f"  [chunk {idx}] sending {chunk.stat().st_size//1024} KB to {AUDIO_LLM} ...")
    for attempt in range(3):
        r = requests.post(f"{BASE}/chat/completions",
                          headers={"Authorization": f"Bearer {API_KEY}"},
                          json=payload, timeout=600)
        if r.status_code == 200:
            break
        print(f"    attempt {attempt+1} failed: {r.status_code} {r.text[:200]}")
        time.sleep(5)
    else:
        raise RuntimeError(f"chunk {idx} failed after retries")

    text = r.json()["choices"][0]["message"]["content"]
    gu, mr = "", text
    if DELIM_MR in text:
        head, mr = text.split(DELIM_MR, 1)
        gu = head.replace(DELIM_GU, "").strip()
    return gu.strip(), mr.strip()


def split_text_for_tts(text: str, limit: int) -> list[str]:
    import re
    # split on Devanagari danda, newlines, and periods
    parts = re.split(r'(?<=[।\.\n])', text)
    chunks, cur = [], ""
    for p in parts:
        if len(cur) + len(p) > limit and cur:
            chunks.append(cur.strip())
            cur = p
        else:
            cur += p
    if cur.strip():
        chunks.append(cur.strip())
    return [c for c in chunks if c.strip()]


def tts_pcm(text: str, idx: int) -> bytes:
    payload = {
        "model": TTS_MODEL,
        "input": text,
        "voice": TTS_VOICE,
        "response_format": "pcm",
    }
    for attempt in range(3):
        r = requests.post(f"{BASE}/audio/speech",
                          headers={"Authorization": f"Bearer {API_KEY}",
                                   "Content-Type": "application/json"},
                          json=payload, timeout=300)
        if r.status_code == 200 and not r.content[:20].lstrip().startswith(b'{"error"'):
            return r.content
        print(f"    tts chunk {idx} attempt {attempt+1}: {r.status_code} {r.content[:150]}")
        time.sleep(4)
    raise RuntimeError(f"tts chunk {idx} failed")


def main():
    if not API_KEY:
        sys.exit("OPENROUTER_API_KEY missing")
    if len(sys.argv) < 2:
        sys.exit("usage: translate_to_marathi.py <job_folder_or_audio_file>")

    try:
        job_dir, audio = resolve_job(sys.argv[1])
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))
    print(f"Job folder: {job_dir}")

    stem = audio.with_suffix("")
    gu_out = Path(f"{stem}.gujarati.txt")
    mr_out = Path(f"{stem}.marathi.txt")
    mp3_out = Path(f"{stem}.marathi.mp3")

    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)

        # --- Step 1-2: transcribe + translate ---
        print("\n=== Step 1-2: Gujarati audio -> Gujarati + Marathi text ===")
        chunks = split_audio(audio, workdir)
        gu_all, mr_all = [], []
        for i, c in enumerate(chunks, 1):
            gu, mr = transcribe_translate_chunk(c, i)
            gu_all.append(gu)
            mr_all.append(mr)
            print(f"  [chunk {i}] gujarati {len(gu)} chars | marathi {len(mr)} chars")

        gujarati = "\n\n".join(gu_all).strip()
        marathi = "\n\n".join(mr_all).strip()
        gu_out.write_text(gujarati, encoding="utf-8")
        mr_out.write_text(marathi, encoding="utf-8")
        print(f"\nSaved transcript: {gu_out}")
        print(f"Saved Marathi:    {mr_out}  ({len(marathi)} chars)")

        # --- Step 3-4: TTS ---
        print("\n=== Step 3: Marathi text -> speech (Gemini TTS) ===")
        tts_chunks = split_text_for_tts(marathi, TTS_CHAR_LIMIT)
        print(f"  {len(tts_chunks)} TTS requests")
        pcm_path = workdir / "marathi.pcm"
        with open(pcm_path, "wb") as f:
            for i, t in enumerate(tts_chunks, 1):
                print(f"  [tts {i}/{len(tts_chunks)}] {len(t)} chars")
                f.write(tts_pcm(t, i))

        print("\n=== Step 4: encode mp3 ===")
        run(["ffmpeg", "-y", "-f", "s16le", "-ar", str(TTS_SAMPLE_RATE), "-ac", "1",
             "-i", str(pcm_path), "-b:a", "128k", str(mp3_out)])

    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_out)],
        capture_output=True, text=True).stdout.strip()
    print(f"\nDONE")
    print(f"  Marathi audio: {mp3_out}  ({mp3_out.stat().st_size//1024} KB, {dur}s)")
    print(f"  Marathi text:  {mr_out}")
    print(f"  Gujarati text: {gu_out}")


if __name__ == "__main__":
    main()
