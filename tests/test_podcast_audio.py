import json
import sys
import tempfile
import unittest
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from podcast_audio import build_turn_prompt, render_podcast


@dataclass(frozen=True)
class Speaker:
    name: str
    voice: str
    style: str


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str
    pause_after_ms: int


@dataclass(frozen=True)
class Episode:
    slug: str
    scene: str
    director_notes: str


@dataclass(frozen=True)
class TTS:
    model: str
    sample_rate: int
    default_pause_ms: int
    fade_ms: int


@dataclass(frozen=True)
class Config:
    episode: Episode
    tts: TTS
    speakers: dict[str, Speaker]
    turns: tuple[Turn, ...]


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.last_generation_id = None

    def synthesize(self, **kwargs):
        self.calls.append(kwargs)
        self.last_generation_id = f"generation-{len(self.calls)}"
        return self.responses.pop(0)


def pcm(*samples):
    return array("h", samples).tobytes()


class PodcastAudioTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(
            episode=Episode(
                slug="test-episode",
                scene="A quiet studio.",
                director_notes="Keep it conversational.",
            ),
            tts=TTS(
                model="test/model",
                sample_rate=24000,
                default_pause_ms=2,
                fade_ms=1,
            ),
            speakers={
                "HOST": Speaker("Maya", "Kore", "Warm and curious."),
                "GUEST": Speaker("Arun", "Puck", "Thoughtful and lively."),
            },
            turns=(
                Turn("HOST", "[excited] Welcome.", 2),
                Turn("GUEST", "Thanks. [laughs]", 999),
            ),
        )
        self.first_pcm = pcm(*([1000] * 48))
        self.second_pcm = pcm(*([-1000] * 48))

    def test_build_turn_prompt_has_exact_sections_and_transcript(self):
        prompt = build_turn_prompt(self.config, self.config.turns[0])

        self.assertEqual(
            prompt,
            "# AUDIO PROFILE\n"
            "Maya: Warm and curious.\n\n"
            "# SCENE\n"
            "A quiet studio.\n\n"
            "# DIRECTOR'S NOTES\n"
            "Keep it conversational.\n\n"
            "Speak only the transcript below. Do not read headings or directions aloud.\n\n"
            "# TRANSCRIPT\n"
            "[excited] Welcome.",
        )

    @patch("podcast_audio.subprocess.run")
    def test_render_assembles_fades_silence_timings_and_manifest(self, run):
        client = FakeClient([self.first_pcm, self.second_pcm])
        with tempfile.TemporaryDirectory() as temporary_directory:
            job_dir = Path(temporary_directory)
            result = render_podcast(self.config, job_dir, client)

            with wave.open(str(result.wav_path), "rb") as wav_file:
                self.assertEqual(wav_file.getparams()[:4], (1, 2, 24000, 144))
                rendered = array("h")
                rendered.frombytes(wav_file.readframes(wav_file.getnframes()))

            self.assertEqual(rendered[0], 0)
            self.assertEqual(rendered[47], 0)
            self.assertEqual(rendered[48:96], array("h", [0] * 48))
            self.assertEqual(rendered[96], 0)
            self.assertEqual(rendered[-1], 0)
            self.assertEqual(
                result.timings,
                (
                    result.timings[0].__class__(0, "HOST", 0, 2),
                    result.timings[0].__class__(1, "GUEST", 4, 6),
                ),
            )

            manifest = json.loads(result.manifest_path.read_text())
            self.assertEqual(len(manifest["config_sha256"]), 64)
            self.assertEqual(manifest["outputs"], {
                "mp3": "test-episode.podcast.mp3",
                "wav": "test-episode.podcast.wav",
            })
            self.assertEqual(
                manifest["timings"],
                [
                    {"end_ms": 2, "index": 0, "speaker": "HOST", "start_ms": 0},
                    {"end_ms": 6, "index": 1, "speaker": "GUEST", "start_ms": 4},
                ],
            )
            self.assertEqual(
                [segment["sample_count"] for segment in manifest["segments"]],
                [48, 48],
            )
            self.assertEqual(
                [segment["generation_id"] for segment in manifest["segments"]],
                ["generation-1", "generation-2"],
            )
            for index, segment in enumerate(manifest["segments"]):
                self.assertTrue(
                    segment["path"].startswith(
                        f".podcast/segments/{index:04d}-"
                    )
                )
                self.assertEqual(len(segment["sha256"]), 64)

            run.assert_called_once_with(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(result.wav_path),
                    "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-b:a",
                    "192k",
                    str(result.mp3_path),
                ],
                check=True,
            )

    @patch("podcast_audio.subprocess.run")
    def test_nonempty_even_segments_are_reused(self, run):
        with tempfile.TemporaryDirectory() as temporary_directory:
            job_dir = Path(temporary_directory)
            first_client = FakeClient([self.first_pcm, self.second_pcm])
            first = render_podcast(self.config, job_dir, first_client)
            first_manifest = json.loads(first.manifest_path.read_text())

            cached_client = FakeClient([])
            second = render_podcast(self.config, job_dir, cached_client)
            second_manifest = json.loads(second.manifest_path.read_text())

            self.assertEqual(cached_client.calls, [])
            self.assertEqual(
                second_manifest["segments"], first_manifest["segments"]
            )
            self.assertEqual(second.timings, first.timings)
            self.assertEqual(run.call_count, 2)

    @patch("podcast_audio.subprocess.run")
    def test_force_regenerates_cached_segments(self, run):
        with tempfile.TemporaryDirectory() as temporary_directory:
            job_dir = Path(temporary_directory)
            render_podcast(
                self.config,
                job_dir,
                FakeClient([self.first_pcm, self.second_pcm]),
            )
            forced_client = FakeClient([self.second_pcm, self.first_pcm])

            render_podcast(self.config, job_dir, forced_client, force=True)

            self.assertEqual(len(forced_client.calls), 2)

    @patch("podcast_audio.subprocess.run")
    def test_invalid_client_pcm_is_not_cached(self, run):
        client = FakeClient([b"\x00"])
        one_turn_config = Config(
            episode=self.config.episode,
            tts=self.config.tts,
            speakers=self.config.speakers,
            turns=(self.config.turns[0],),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            job_dir = Path(temporary_directory)
            with self.assertRaisesRegex(RuntimeError, "invalid"):
                render_podcast(one_turn_config, job_dir, client)

            self.assertEqual(
                list((job_dir / ".podcast" / "segments").glob("*.pcm")),
                [],
            )
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
