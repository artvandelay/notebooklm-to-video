import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.youtube_package import _format_timestamp, render_youtube_package


@dataclass(frozen=True)
class Timing:
    start_ms: int


def make_config(*, title="Episode title", description="", tags=("one", "two")):
    return SimpleNamespace(
        episode=SimpleNamespace(
            slug="sample-episode",
            title="Episode title",
            language="en",
            summary="A useful summary.",
        ),
        youtube=SimpleNamespace(
            title=title,
            description=description,
            tags=tags,
            category="Education",
        ),
        chapters=(
            SimpleNamespace(title="Introduction", turn=0),
            SimpleNamespace(title="Deep Dive", turn=1),
        ),
    )


class TimestampTests(unittest.TestCase):
    def test_timestamp_boundaries(self):
        self.assertEqual(_format_timestamp(0), "00:00")
        self.assertEqual(_format_timestamp(59_999), "00:59")
        self.assertEqual(_format_timestamp(60_000), "01:00")
        self.assertEqual(_format_timestamp(3_599_999), "59:59")
        self.assertEqual(_format_timestamp(3_600_000), "1:00:00")


class YouTubePackageTests(unittest.TestCase):
    def test_renders_chapters_filenames_and_default_title(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample-episode.youtube.md"
            result = render_youtube_package(
                make_config(),
                (Timing(0), Timing(65_432)),
                output,
            )

            self.assertEqual(result, output)
            text = output.read_text(encoding="utf-8")
            self.assertIn("# Title\nEpisode title", text)
            self.assertIn("# Chapters\n00:00 Introduction\n01:05 Deep Dive", text)
            self.assertIn("- Thumbnail filename: sample-episode.png", text)
            self.assertIn("- Video filename: sample-episode_video.mp4", text)

    def test_description_composition_tags_unicode_and_section_order(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "metadata.md"
            config = make_config(
                title="ગુજરાતી વાર્તા",
                description="पहली पंक्ति",
                tags=("ગુજરાતી", "मराठी"),
            )
            render_youtube_package(config, (Timing(0), Timing(1000)), output)

            text = output.read_text(encoding="utf-8")
            self.assertIn("# Description\nपहली पंक्ति\n\nA useful summary.", text)
            self.assertIn("# Tags\nગુજરાતી, मराठी", text)
            headings = [
                "# Title",
                "# Description",
                "# Chapters",
                "# Tags",
                "# Upload settings",
            ]
            self.assertEqual(
                [text.index(heading) for heading in headings],
                sorted(text.index(heading) for heading in headings),
            )

    def test_empty_description_omits_prefix_spacing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "metadata.md"
            render_youtube_package(
                make_config(description=""),
                (Timing(0), Timing(1000)),
                output,
            )
            self.assertIn("# Description\nA useful summary.\n\n# Chapters", output.read_text())

    def test_writes_through_sibling_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "metadata.md"
            with patch("src.youtube_package.os.replace", wraps=__import__("os").replace) as replace:
                render_youtube_package(
                    make_config(),
                    (Timing(0), Timing(1000)),
                    output,
                )

            replace.assert_called_once_with(Path(f"{output}.tmp"), output)
            self.assertFalse(Path(f"{output}.tmp").exists())


if __name__ == "__main__":
    unittest.main()
