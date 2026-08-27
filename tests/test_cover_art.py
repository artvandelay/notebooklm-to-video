import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src import cover_art


PNG_BYTES = b"\x89PNG\r\n\x1a\none-pixel"
PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode("ascii")


def image_response(data_url=PNG_DATA_URL):
    response = Mock(status_code=200)
    response.json.return_value = {
        "choices": [
            {"message": {"images": [{"image_url": {"url": data_url}}]}}
        ]
    }
    return response


class CoverArtTests(unittest.TestCase):
    def setUp(self):
        self.api_key = patch.object(cover_art, "OPENROUTER_API_KEY", "test-key")
        self.api_key.start()
        self.addCleanup(self.api_key.stop)

    def test_preserves_default_timestamp_naming(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(cover_art, "get_image_prompt", return_value="wrapped"),
                patch.object(cover_art.time, "time", return_value=1234),
                patch.object(cover_art.requests, "post", return_value=image_response()),
            ):
                result = cover_art.generate_cover_art("transcript", directory)

            expected = Path(directory) / "cover_art_1234.png"
            self.assertEqual(result, str(expected))
            self.assertEqual(expected.read_bytes(), PNG_BYTES)

    def test_prompt_override_is_sent_exactly_and_timeout_is_set(self):
        prompt = "Exact prompt " + ("x" * 1000)
        with tempfile.TemporaryDirectory() as directory:
            post = Mock(return_value=image_response())
            with (
                patch.object(cover_art, "get_image_prompt") as get_prompt,
                patch.object(cover_art.requests, "post", post),
            ):
                cover_art.generate_cover_art(
                    "ignored transcript",
                    directory,
                    prompt_override=prompt,
                )

            get_prompt.assert_not_called()
            _, kwargs = post.call_args
            self.assertEqual(
                kwargs["json"]["messages"],
                [{"role": "user", "content": prompt}],
            )
            self.assertEqual(kwargs["timeout"], 180)

    def test_writes_exact_canonical_output_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "episode.png"
            with (
                patch.object(cover_art.requests, "post", return_value=image_response()),
                patch.object(cover_art.os, "replace", wraps=cover_art.os.replace) as replace,
            ):
                result = cover_art.generate_cover_art(
                    "transcript",
                    directory,
                    output_path=output,
                )

            self.assertEqual(result, str(output))
            self.assertEqual(output.read_bytes(), PNG_BYTES)
            replace.assert_called_once_with(Path(f"{output}.tmp"), output)

    def test_rejects_output_outside_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).parent / "escape.png"
            with patch.object(cover_art.requests, "post") as post:
                with self.assertRaisesRegex(ValueError, "directly inside"):
                    cover_art.generate_cover_art(
                        "transcript",
                        directory,
                        output_path=output,
                    )
            post.assert_not_called()

    def test_rejects_malformed_data_url(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                cover_art.requests,
                "post",
                return_value=image_response("not-a-data-url"),
            ):
                with self.assertRaises(ValueError):
                    cover_art.generate_cover_art("transcript", directory)


if __name__ == "__main__":
    unittest.main()
