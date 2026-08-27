"""Resumable rendering and mastering for scripted podcast audio."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import wave
from array import array
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openrouter_tts import OpenRouterTTSClient
    from podcast_config import PodcastConfig, TurnConfig


@dataclass(frozen=True)
class TurnTiming:
    index: int
    speaker: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class RenderResult:
    wav_path: Path
    mp3_path: Path
    manifest_path: Path
    timings: tuple[TurnTiming, ...]


def build_turn_prompt(config: PodcastConfig, turn: TurnConfig) -> str:
    """Build the structured Gemini TTS prompt for one dialogue turn."""
    speaker = config.speakers[turn.speaker]
    return (
        "# AUDIO PROFILE\n"
        f"{speaker.name}: {speaker.style}\n\n"
        "# SCENE\n"
        f"{config.episode.scene}\n\n"
        "# DIRECTOR'S NOTES\n"
        f"{config.episode.director_notes}\n\n"
        "Speak only the transcript below. Do not read headings or directions aloud.\n\n"
        "# TRANSCRIPT\n"
        f"{turn.text}"
    )


def _canonical_json(value: Any) -> bytes:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _turn_hash(config: PodcastConfig, turn: TurnConfig) -> str:
    speaker = config.speakers[turn.speaker]
    payload = {
        "model": config.tts.model,
        "sample_rate": config.tts.sample_rate,
        "speaker": {
            "id": turn.speaker,
            "name": speaker.name,
            "voice": speaker.voice,
            "style": speaker.style,
        },
        "scene": config.episode.scene,
        "director_notes": config.episode.director_notes,
        "text": turn.text,
        "pause_after_ms": turn.pause_after_ms,
        "fade_ms": config.tts.fade_ms,
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _write_bytes_atomically(path: Path, content: bytes) -> None:
    tmp_path = Path(f"{path}.tmp")
    try:
        tmp_path.write_bytes(content)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_json_atomically(path: Path, value: Any) -> None:
    content = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    _write_bytes_atomically(path, content)


def _pcm_samples(content: bytes) -> array:
    if not content or len(content) % 2:
        raise RuntimeError("TTS returned invalid signed 16-bit PCM")
    samples = array("h")
    samples.frombytes(content)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def _fade(samples: array, fade_samples: int) -> None:
    count = min(fade_samples, len(samples))
    if count <= 0:
        return
    if count == 1:
        samples[0] = 0
        return
    denominator = count - 1
    original = array("h", samples)
    last_index = len(samples) - 1
    for index, value in enumerate(original):
        fade_in = min(index / denominator, 1.0)
        fade_out = min((last_index - index) / denominator, 1.0)
        samples[index] = int(value * min(fade_in, fade_out))


def _samples_to_bytes(samples: array) -> bytes:
    output = array("h", samples)
    if sys.byteorder != "little":
        output.byteswap()
    return output.tobytes()


def _write_wav_atomically(path: Path, samples: array, sample_rate: int) -> None:
    tmp_path = Path(f"{path}.tmp")
    try:
        with wave.open(str(tmp_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(_samples_to_bytes(samples))
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _existing_generation_ids(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.is_file():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    generation_ids = {}
    for segment in manifest.get("segments", []):
        path = segment.get("path")
        generation_id = segment.get("generation_id")
        if isinstance(path, str) and isinstance(generation_id, str):
            generation_ids[path] = generation_id
    return generation_ids


def render_podcast(
    config: PodcastConfig,
    job_dir: Path,
    client: OpenRouterTTSClient,
    *,
    force: bool = False,
) -> RenderResult:
    """Render cached turns, assemble WAV audio, and master it to MP3."""
    job_dir = Path(job_dir)
    segments_dir = job_dir / ".podcast" / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = job_dir / ".podcast" / "manifest.json"
    wav_path = job_dir / f"{config.episode.slug}.podcast.wav"
    mp3_path = job_dir / f"{config.episode.slug}.podcast.mp3"

    prior_generation_ids = _existing_generation_ids(manifest_path)
    assembled = array("h")
    timings = []
    manifest_segments = []
    sample_rate = config.tts.sample_rate
    fade_samples = config.tts.fade_ms * sample_rate // 1000

    for index, turn in enumerate(config.turns):
        speaker = config.speakers[turn.speaker]
        segment_hash = _turn_hash(config, turn)
        segment_path = (
            segments_dir
            / f"{index:04d}-{turn.speaker}-{segment_hash}.pcm"
        )
        relative_segment_path = segment_path.relative_to(job_dir).as_posix()
        cached = (
            not force
            and segment_path.is_file()
            and segment_path.stat().st_size > 0
            and segment_path.stat().st_size % 2 == 0
        )

        generation_id = prior_generation_ids.get(relative_segment_path)
        if cached:
            pcm = segment_path.read_bytes()
        else:
            pcm = client.synthesize(
                model=config.tts.model,
                voice=speaker.voice,
                text=build_turn_prompt(config, turn),
            )
            if not pcm or len(pcm) % 2:
                raise RuntimeError("TTS returned invalid signed 16-bit PCM")
            _write_bytes_atomically(segment_path, pcm)
            value = getattr(client, "last_generation_id", None)
            generation_id = value if isinstance(value, str) and value else None

        samples = _pcm_samples(pcm)
        _fade(samples, fade_samples)
        start_sample = len(assembled)
        assembled.extend(samples)
        end_sample = len(assembled)
        timing = TurnTiming(
            index=index,
            speaker=turn.speaker,
            start_ms=start_sample * 1000 // sample_rate,
            end_ms=end_sample * 1000 // sample_rate,
        )
        timings.append(timing)

        segment_record = {
            "index": index,
            "speaker": turn.speaker,
            "path": relative_segment_path,
            "sha256": segment_hash,
            "sample_count": len(samples),
        }
        if generation_id is not None:
            segment_record["generation_id"] = generation_id
        manifest_segments.append(segment_record)

        if index < len(config.turns) - 1:
            silence_samples = turn.pause_after_ms * sample_rate // 1000
            assembled.extend(array("h", [0]) * silence_samples)

    _write_wav_atomically(wav_path, assembled, sample_rate)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "192k",
            str(mp3_path),
        ],
        check=True,
    )

    timing_records = [asdict(timing) for timing in timings]
    manifest = {
        "config_sha256": hashlib.sha256(_canonical_json(config)).hexdigest(),
        "segments": manifest_segments,
        "timings": timing_records,
        "outputs": {
            "wav": wav_path.relative_to(job_dir).as_posix(),
            "mp3": mp3_path.relative_to(job_dir).as_posix(),
        },
    }
    _write_json_atomically(manifest_path, manifest)

    return RenderResult(
        wav_path=wav_path,
        mp3_path=mp3_path,
        manifest_path=manifest_path,
        timings=tuple(timings),
    )
