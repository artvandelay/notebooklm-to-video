from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.podcast_audio import TurnTiming
    from src.podcast_config import PodcastConfig


def _format_timestamp(milliseconds: int) -> str:
    total_seconds = milliseconds // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def render_youtube_package(
    config: PodcastConfig,
    timings: tuple[TurnTiming, ...],
    output_path: Path,
) -> Path:
    """Write the metadata needed for a manual YouTube upload."""
    chapters = [
        f"{_format_timestamp(timings[chapter.turn].start_ms)} {chapter.title}"
        for chapter in config.chapters
    ]

    description_parts = []
    if config.youtube.description:
        description_parts.append(config.youtube.description)
    description_parts.append(config.episode.summary)
    description = "\n\n".join(description_parts)

    content = "\n".join(
        [
            "# Title",
            config.youtube.title,
            "",
            "# Description",
            description,
            "",
            "# Chapters",
            *chapters,
            "",
            "# Tags",
            ", ".join(config.youtube.tags),
            "",
            "# Upload settings",
            f"- Language: {config.episode.language}",
            f"- Category: {config.youtube.category}",
            "- Made for kids: No",
            "- Visibility: Unlisted first",
            f"- Thumbnail filename: {config.episode.slug}.png",
            f"- Video filename: {config.episode.slug}_video.mp4",
            "",
        ]
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(f"{output_path}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    os.replace(temporary_path, output_path)
    return output_path
