"""Per-upload job folders.

Each episode lives in uploads/<name>/ with its audio, cover, transcripts, and video.
Pass either that folder or an audio file inside it.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = REPO_ROOT / "uploads"

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"}


def find_audio(job_dir: Path) -> Path:
    candidates = []
    for path in job_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTS:
            continue
        if path.name.endswith(".marathi.mp3"):
            continue
        candidates.append(path)

    if not candidates:
        raise FileNotFoundError(
            f"No audio file found in {job_dir}. "
            f"Put an .m4a/.mp3/.wav in that folder."
        )

    for path in candidates:
        if path.stem == job_dir.name:
            return path
    if len(candidates) == 1:
        return candidates[0]
    names = ", ".join(p.name for p in candidates)
    raise ValueError(f"Multiple audio files in {job_dir}: {names}")


def resolve_job(input_path: str | Path) -> tuple[Path, Path]:
    """Return (job_dir, audio_file) for a folder or audio file path."""
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Not found: {input_path}")

    if path.is_dir():
        job_dir = path
        audio = find_audio(job_dir)
        return job_dir, audio

    if path.suffix.lower() not in AUDIO_EXTS | {".mp4"}:
        raise ValueError(f"Not an audio file or job folder: {path}")

    parent = path.parent
    if parent == REPO_ROOT:
        job_dir = UPLOADS_DIR / path.stem
        job_dir.mkdir(parents=True, exist_ok=True)
        dest = job_dir / path.name
        if path != dest:
            path.rename(dest)
        return job_dir, dest

    return parent, path
