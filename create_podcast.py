#!/usr/bin/env python3
"""Create mastered podcast and YouTube assets from podcast.json."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

from cover_art import generate_cover_art
from openrouter_tts import OpenRouterTTSClient
from podcast_audio import render_podcast
from podcast_config import load_podcast_config, resolve_podcast_config
from video import create_video
from youtube_package import render_youtube_package


def _art_prompt(config, transcript: str) -> str:
    return (
        f"Episode title: {config.episode.title}\n"
        f"Summary: {config.episode.summary}\n"
        f"Art prompt: {config.episode.art_prompt}\n"
        f"Transcript excerpt: {transcript[:1200]}"
    )


def _copy_atomic(source: Path, destination: Path) -> None:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Cover art file not found: {source}")
    if source == destination.resolve():
        return

    temporary = destination.with_name(f"{destination.name}.tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)


def run_pipeline(
    config_input,
    *,
    cover_art_path=None,
    force_audio=False,
    force_art=False,
    auto_approve=False,
) -> dict[str, Path]:
    """Render podcast audio, cover art, video, and YouTube metadata."""
    config_path = resolve_podcast_config(config_input)
    config = load_podcast_config(config_path)
    job_dir = config_path.parent

    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    client = OpenRouterTTSClient(api_key)
    rendered = render_podcast(config, job_dir, client, force=force_audio)

    cover_path = job_dir / f"{config.episode.slug}.png"
    video_path = job_dir / f"{config.episode.slug}_video.mp4"
    youtube_path = job_dir / f"{config.episode.slug}.youtube.md"
    outputs = {
        "wav": rendered.wav_path,
        "mp3": rendered.mp3_path,
        "manifest": rendered.manifest_path,
        "cover": cover_path,
        "video": video_path,
        "youtube": youtube_path,
    }

    if cover_art_path is not None:
        _copy_atomic(Path(cover_art_path), cover_path)
    elif force_art or not cover_path.is_file() or cover_path.stat().st_size == 0:
        transcript = "\n".join(turn.text for turn in config.turns)
        generate_cover_art(
            transcript,
            output_dir=str(job_dir),
            output_path=cover_path,
            prompt_override=_art_prompt(config, transcript),
        )

    print("Planned outputs:")
    for name in ("wav", "mp3", "manifest", "cover", "video", "youtube"):
        print(f"  {outputs[name]}")

    if not auto_approve:
        approval = input("Proceed with video creation? (y/n): ").strip().lower()
        if approval != "y":
            print("Video creation cancelled by user")
            return outputs

    create_video(
        str(cover_path),
        str(rendered.mp3_path),
        str(video_path),
        resolution=(1920, 1080),
    )
    render_youtube_package(config, rendered.timings, youtube_path)
    return outputs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create podcast audio and manual YouTube upload assets"
    )
    parser.add_argument(
        "config_or_folder",
        help="uploads/<episode>/podcast.json or its episode folder",
    )
    parser.add_argument("--cover-art", help="Use an existing cover image")
    parser.add_argument(
        "--force-audio",
        action="store_true",
        help="Regenerate cached audio segments",
    )
    parser.add_argument(
        "--force-art",
        action="store_true",
        help="Regenerate cover art",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Create video without prompting",
    )
    parser.add_argument("--version", action="version", version="Podcast Creator v1.0.0")
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        run_pipeline(
            args.config_or_folder,
            cover_art_path=args.cover_art,
            force_audio=args.force_audio,
            force_art=args.force_art,
            auto_approve=args.auto_approve,
        )
    except (
        ValueError,
        FileNotFoundError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
