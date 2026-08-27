"""Strict loading and validation for podcast.json files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = REPO_ROOT / "uploads"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class SpeakerConfig:
    name: str
    voice: str
    style: str


@dataclass(frozen=True)
class TurnConfig:
    speaker: str
    text: str
    pause_after_ms: int


@dataclass(frozen=True)
class ChapterConfig:
    title: str
    turn: int


@dataclass(frozen=True)
class TTSConfig:
    model: str
    sample_rate: int
    default_pause_ms: int
    fade_ms: int


@dataclass(frozen=True)
class EpisodeMetadata:
    slug: str
    title: str
    language: str
    summary: str
    art_prompt: str
    scene: str
    director_notes: str


@dataclass(frozen=True)
class YouTubeConfig:
    title: str
    description: str
    tags: tuple[str, ...]
    category: str


@dataclass(frozen=True)
class PodcastConfig:
    version: int
    episode: EpisodeMetadata
    tts: TTSConfig
    speakers: dict[str, SpeakerConfig]
    turns: tuple[TurnConfig, ...]
    chapters: tuple[ChapterConfig, ...]
    youtube: YouTubeConfig


def _error(path: str, message: str) -> ValueError:
    return ValueError(f"{path}: {message}")


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "must be an object")
    return value


def _reject_unknown(
    value: dict[str, Any], allowed: set[str], path: str
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise _error(f"{path}.{unknown[0]}", "unknown key")


def _required(value: dict[str, Any], key: str, path: str) -> Any:
    if key not in value:
        raise _error(f"{path}.{key}", "is required")
    return value[key]


def _string(value: Any, path: str, *, non_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise _error(path, "must be a string")
    if non_empty and not value.strip():
        raise _error(path, "must be non-empty")
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(path, "must be an integer")
    return value


def _bounded_integer(value: Any, path: str, minimum: int, maximum: int) -> int:
    result = _integer(value, path)
    if not minimum <= result <= maximum:
        raise _error(path, f"must be between {minimum} and {maximum}")
    return result


def _parse_episode(value: Any) -> EpisodeMetadata:
    path = "$.episode"
    obj = _object(value, path)
    keys = {
        "slug",
        "title",
        "language",
        "summary",
        "art_prompt",
        "scene",
        "director_notes",
    }
    _reject_unknown(obj, keys, path)
    slug = _string(_required(obj, "slug", path), f"{path}.slug")
    if not SLUG_PATTERN.fullmatch(slug):
        raise _error(f"{path}.slug", "must match ^[a-z0-9]+(?:-[a-z0-9]+)*$")
    return EpisodeMetadata(
        slug=slug,
        title=_string(_required(obj, "title", path), f"{path}.title"),
        language=_string(_required(obj, "language", path), f"{path}.language"),
        summary=_string(_required(obj, "summary", path), f"{path}.summary"),
        art_prompt=_string(
            _required(obj, "art_prompt", path), f"{path}.art_prompt", non_empty=False
        ),
        scene=_string(_required(obj, "scene", path), f"{path}.scene"),
        director_notes=_string(
            _required(obj, "director_notes", path), f"{path}.director_notes"
        ),
    )


def _parse_tts(value: Any) -> TTSConfig:
    path = "$.tts"
    obj = _object(value, path)
    keys = {"model", "sample_rate", "default_pause_ms", "fade_ms"}
    _reject_unknown(obj, keys, path)
    sample_rate = _integer(
        _required(obj, "sample_rate", path), f"{path}.sample_rate"
    )
    if sample_rate != 24000:
        raise _error(f"{path}.sample_rate", "must equal 24000")
    return TTSConfig(
        model=_string(_required(obj, "model", path), f"{path}.model"),
        sample_rate=sample_rate,
        default_pause_ms=_bounded_integer(
            _required(obj, "default_pause_ms", path),
            f"{path}.default_pause_ms",
            0,
            5000,
        ),
        fade_ms=_bounded_integer(
            _required(obj, "fade_ms", path), f"{path}.fade_ms", 0, 50
        ),
    )


def _parse_speakers(value: Any) -> dict[str, SpeakerConfig]:
    path = "$.speakers"
    obj = _object(value, path)
    if not 1 <= len(obj) <= 2:
        raise _error(path, "must contain one or two speakers")
    speakers: dict[str, SpeakerConfig] = {}
    for speaker_id, raw_speaker in obj.items():
        speaker_path = f"{path}.{speaker_id}"
        _string(speaker_id, speaker_path)
        speaker = _object(raw_speaker, speaker_path)
        keys = {"name", "voice", "style"}
        _reject_unknown(speaker, keys, speaker_path)
        speakers[speaker_id] = SpeakerConfig(
            name=_string(
                _required(speaker, "name", speaker_path), f"{speaker_path}.name"
            ),
            voice=_string(
                _required(speaker, "voice", speaker_path), f"{speaker_path}.voice"
            ),
            style=_string(
                _required(speaker, "style", speaker_path), f"{speaker_path}.style"
            ),
        )
    return speakers


def _parse_turns(
    value: Any, speakers: dict[str, SpeakerConfig], default_pause_ms: int
) -> tuple[TurnConfig, ...]:
    path = "$.turns"
    if not isinstance(value, list):
        raise _error(path, "must be an array")
    if not value:
        raise _error(path, "must contain at least one turn")
    turns = []
    for index, raw_turn in enumerate(value):
        turn_path = f"{path}[{index}]"
        turn = _object(raw_turn, turn_path)
        keys = {"speaker", "text", "pause_after_ms"}
        _reject_unknown(turn, keys, turn_path)
        speaker = _string(
            _required(turn, "speaker", turn_path), f"{turn_path}.speaker"
        )
        if speaker not in speakers:
            raise _error(f"{turn_path}.speaker", f"unknown speaker {speaker!r}")
        pause = turn.get("pause_after_ms", default_pause_ms)
        turns.append(
            TurnConfig(
                speaker=speaker,
                text=_string(
                    _required(turn, "text", turn_path), f"{turn_path}.text"
                ),
                pause_after_ms=_bounded_integer(
                    pause, f"{turn_path}.pause_after_ms", 0, 5000
                ),
            )
        )
    return tuple(turns)


def _parse_chapters(value: Any, turn_count: int) -> tuple[ChapterConfig, ...]:
    path = "$.chapters"
    if value is None:
        return (ChapterConfig(title="Introduction", turn=0),)
    if not isinstance(value, list):
        raise _error(path, "must be an array")
    if not value:
        return (ChapterConfig(title="Introduction", turn=0),)
    chapters = []
    previous = -1
    for index, raw_chapter in enumerate(value):
        chapter_path = f"{path}[{index}]"
        chapter = _object(raw_chapter, chapter_path)
        keys = {"title", "turn"}
        _reject_unknown(chapter, keys, chapter_path)
        turn = _integer(
            _required(chapter, "turn", chapter_path), f"{chapter_path}.turn"
        )
        if not 0 <= turn < turn_count:
            raise _error(
                f"{chapter_path}.turn", f"must be between 0 and {turn_count - 1}"
            )
        if turn <= previous:
            raise _error(
                f"{chapter_path}.turn", "indices must be unique and ascending"
            )
        chapters.append(
            ChapterConfig(
                title=_string(
                    _required(chapter, "title", chapter_path),
                    f"{chapter_path}.title",
                ),
                turn=turn,
            )
        )
        previous = turn
    return tuple(chapters)


def _parse_youtube(value: Any, episode_title: str) -> YouTubeConfig:
    path = "$.youtube"
    if value is None:
        obj: dict[str, Any] = {}
    else:
        obj = _object(value, path)
    keys = {"title", "description", "tags", "category"}
    _reject_unknown(obj, keys, path)
    tags_value = obj.get("tags", [])
    if not isinstance(tags_value, list):
        raise _error(f"{path}.tags", "must be an array")
    tags = tuple(
        _string(tag, f"{path}.tags[{index}]")
        for index, tag in enumerate(tags_value)
    )
    return YouTubeConfig(
        title=_string(obj.get("title", episode_title), f"{path}.title"),
        description=_string(
            obj.get("description", ""), f"{path}.description", non_empty=False
        ),
        tags=tags,
        category=_string(obj.get("category", "Education"), f"{path}.category"),
    )


def resolve_podcast_config(input_path: str | Path) -> Path:
    """Resolve an uploads directory or JSON file without modifying the filesystem."""
    path = Path(input_path).expanduser().resolve()
    uploads_dir = UPLOADS_DIR.expanduser().resolve()
    try:
        path.relative_to(uploads_dir)
    except ValueError as exc:
        raise ValueError(f"{path}: must be inside {uploads_dir}") from exc
    if not path.exists():
        raise FileNotFoundError(f"Not found: {input_path}")
    if path.is_dir():
        config_path = path / "podcast.json"
    elif path.suffix.lower() == ".json":
        config_path = path
    else:
        raise ValueError(f"{path}: must be a directory or .json file")
    if not config_path.is_file():
        raise FileNotFoundError(f"Not found: {config_path}")
    return config_path


def load_podcast_config(path: str | Path) -> PodcastConfig:
    """Load a podcast configuration from a JSON file."""
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"$: invalid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    root = _object(raw, "$")
    keys = {
        "version",
        "episode",
        "tts",
        "speakers",
        "turns",
        "chapters",
        "youtube",
    }
    _reject_unknown(root, keys, "$")
    version = _integer(_required(root, "version", "$"), "$.version")
    if version != 1:
        raise _error("$.version", "must equal 1")
    episode = _parse_episode(_required(root, "episode", "$"))
    tts = _parse_tts(_required(root, "tts", "$"))
    speakers = _parse_speakers(_required(root, "speakers", "$"))
    turns = _parse_turns(
        _required(root, "turns", "$"), speakers, tts.default_pause_ms
    )
    chapters = _parse_chapters(root.get("chapters"), len(turns))
    youtube = _parse_youtube(root.get("youtube"), episode.title)
    return PodcastConfig(
        version=version,
        episode=episode,
        tts=tts,
        speakers=speakers,
        turns=turns,
        chapters=chapters,
        youtube=youtube,
    )
