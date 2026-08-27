import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import podcast_config


def valid_config():
    return {
        "version": 1,
        "episode": {
            "slug": "example-episode",
            "title": "Example Episode",
            "language": "en",
            "summary": "A concise summary.",
            "art_prompt": "An editorial illustration.",
            "scene": "A quiet professional studio.",
            "director_notes": "Use natural conversation.",
        },
        "tts": {
            "model": "google/gemini-3.1-flash-tts-preview",
            "sample_rate": 24000,
            "default_pause_ms": 180,
            "fade_ms": 8,
        },
        "speakers": {
            "HOST": {
                "name": "Maya",
                "voice": "Kore",
                "style": "Warm and curious.",
            },
            "GUEST": {
                "name": "Arun",
                "voice": "Puck",
                "style": "Thoughtful and conversational.",
            },
        },
        "turns": [
            {"speaker": "HOST", "text": "Welcome.", "pause_after_ms": 140},
            {"speaker": "GUEST", "text": "Thanks."},
        ],
        "chapters": [{"title": "Introduction", "turn": 0}],
        "youtube": {
            "title": "Search title",
            "description": "Description prefix",
            "tags": ["podcast", "education"],
            "category": "Education",
        },
    }


class PodcastConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.uploads = Path(self.temporary_directory.name).resolve()
        self.episode_dir = self.uploads / "example-episode"
        self.episode_dir.mkdir()
        self.config_path = self.episode_dir / "podcast.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, data):
        self.config_path.write_text(json.dumps(data), encoding="utf-8")

    def assert_path_error(self, data, expected_path):
        self.write(data)
        with self.assertRaises(ValueError) as context:
            podcast_config.load_podcast_config(self.config_path)
        self.assertIn(expected_path, str(context.exception))

    def test_loads_valid_config_into_frozen_dataclasses(self):
        self.write(valid_config())

        config = podcast_config.load_podcast_config(self.config_path)

        self.assertEqual(config.episode.slug, "example-episode")
        self.assertEqual(config.speakers["HOST"].voice, "Kore")
        self.assertIsInstance(config.turns, tuple)
        self.assertIsInstance(config.chapters, tuple)
        self.assertEqual(config.turns[1].pause_after_ms, 180)
        with self.assertRaises(AttributeError):
            config.version = 2

    def test_resolves_directory_and_json_file_inside_uploads(self):
        self.write(valid_config())
        with patch.object(podcast_config, "UPLOADS_DIR", self.uploads):
            self.assertEqual(
                podcast_config.resolve_podcast_config(self.episode_dir),
                self.config_path,
            )
            self.assertEqual(
                podcast_config.resolve_podcast_config(self.config_path),
                self.config_path,
            )

    def test_resolution_rejects_outside_uploads_and_missing_files(self):
        self.write(valid_config())
        outside = self.uploads.parent / "outside-podcast.json"
        with patch.object(podcast_config, "UPLOADS_DIR", self.uploads):
            with self.assertRaisesRegex(ValueError, "must be inside"):
                podcast_config.resolve_podcast_config(outside)
            with self.assertRaises(FileNotFoundError):
                podcast_config.resolve_podcast_config(
                    self.uploads / "missing" / "podcast.json"
                )

    def test_defaults_chapters_turn_pause_and_youtube(self):
        data = valid_config()
        data.pop("chapters")
        data.pop("youtube")
        data["turns"][0].pop("pause_after_ms")
        self.write(data)

        config = podcast_config.load_podcast_config(self.config_path)

        self.assertEqual(config.turns[0].pause_after_ms, 180)
        self.assertEqual(config.chapters[0].title, "Introduction")
        self.assertEqual(config.chapters[0].turn, 0)
        self.assertEqual(config.youtube.title, "Example Episode")
        self.assertEqual(config.youtube.description, "")
        self.assertEqual(config.youtube.tags, ())
        self.assertEqual(config.youtube.category, "Education")

    def test_rejects_unknown_keys_at_every_object_level(self):
        mutations = [
            (lambda data: data.update(extra=True), "$.extra"),
            (lambda data: data["episode"].update(extra=True), "$.episode.extra"),
            (lambda data: data["tts"].update(extra=True), "$.tts.extra"),
            (
                lambda data: data["speakers"]["HOST"].update(extra=True),
                "$.speakers.HOST.extra",
            ),
            (lambda data: data["turns"][0].update(extra=True), "$.turns[0].extra"),
            (
                lambda data: data["chapters"][0].update(extra=True),
                "$.chapters[0].extra",
            ),
            (lambda data: data["youtube"].update(extra=True), "$.youtube.extra"),
        ]
        for mutate, expected_path in mutations:
            with self.subTest(path=expected_path):
                data = valid_config()
                mutate(data)
                self.assert_path_error(data, expected_path)

    def test_rejects_bad_speaker_reference(self):
        data = valid_config()
        data["turns"][0]["speaker"] = "UNKNOWN"
        self.assert_path_error(data, "$.turns[0].speaker")

    def test_rejects_duplicate_descending_and_out_of_range_chapters(self):
        bad_chapters = [
            [
                {"title": "First", "turn": 0},
                {"title": "Duplicate", "turn": 0},
            ],
            [
                {"title": "Second", "turn": 1},
                {"title": "First", "turn": 0},
            ],
            [{"title": "Missing", "turn": 2}],
        ]
        for chapters in bad_chapters:
            with self.subTest(chapters=chapters):
                data = valid_config()
                data["chapters"] = chapters
                self.assert_path_error(data, "$.chapters")

    def test_rejects_bad_slug(self):
        for slug in ("Bad-Slug", "bad_slug", "-bad", "bad-"):
            with self.subTest(slug=slug):
                data = valid_config()
                data["episode"]["slug"] = slug
                self.assert_path_error(data, "$.episode.slug")

    def test_rejects_out_of_range_pause(self):
        for pause in (-1, 5001):
            with self.subTest(pause=pause):
                data = valid_config()
                data["turns"][0]["pause_after_ms"] = pause
                self.assert_path_error(data, "$.turns[0].pause_after_ms")

    def test_rejects_invalid_fixed_ranges_and_version(self):
        mutations = [
            (lambda data: data.update(version=2), "$.version"),
            (lambda data: data["tts"].update(sample_rate=48000), "$.tts.sample_rate"),
            (
                lambda data: data["tts"].update(default_pause_ms=5001),
                "$.tts.default_pause_ms",
            ),
            (lambda data: data["tts"].update(fade_ms=51), "$.tts.fade_ms"),
        ]
        for mutate, expected_path in mutations:
            with self.subTest(path=expected_path):
                data = copy.deepcopy(valid_config())
                mutate(data)
                self.assert_path_error(data, expected_path)


if __name__ == "__main__":
    unittest.main()
