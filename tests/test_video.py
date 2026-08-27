import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.video import create_video


def expected_command(image, audio, output, filter_value=None):
    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image),
        "-i",
        str(audio),
    ]
    if filter_value is not None:
        command.extend(["-vf", filter_value])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


class VideoTests(unittest.TestCase):
    def make_inputs(self, directory):
        image = Path(directory) / "cover.png"
        audio = Path(directory) / "audio.mp3"
        image.write_bytes(b"image")
        audio.write_bytes(b"audio")
        return image, audio

    def test_default_command_and_backward_compatible_call(self):
        with tempfile.TemporaryDirectory() as directory:
            image, audio = self.make_inputs(directory)
            output = Path(directory) / "video.mp4"
            with patch("src.video.subprocess.run") as run:
                create_video(str(image), str(audio), str(output))

            run.assert_called_once_with(
                expected_command(image, audio, output),
                check=True,
            )

    def test_1920_by_1080_command_and_parent_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            image, audio = self.make_inputs(directory)
            output = Path(directory) / "nested" / "deeper" / "video.mp4"
            video_filter = (
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
            )
            with patch("src.video.subprocess.run") as run:
                create_video(
                    str(image),
                    str(audio),
                    str(output),
                    resolution=(1920, 1080),
                )

            self.assertTrue(output.parent.is_dir())
            run.assert_called_once_with(
                expected_command(image, audio, output, video_filter),
                check=True,
            )

    def test_missing_image_raises_without_invoking_ffmpeg(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "audio.mp3"
            audio.write_bytes(b"audio")
            with patch("src.video.subprocess.run") as run:
                with self.assertRaisesRegex(FileNotFoundError, "Image file"):
                    create_video(
                        str(Path(directory) / "missing.png"),
                        str(audio),
                        str(Path(directory) / "video.mp4"),
                    )
            run.assert_not_called()

    def test_missing_audio_raises_without_invoking_ffmpeg(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "cover.png"
            image.write_bytes(b"image")
            with patch("src.video.subprocess.run") as run:
                with self.assertRaisesRegex(FileNotFoundError, "Audio file"):
                    create_video(
                        str(image),
                        str(Path(directory) / "missing.mp3"),
                        str(Path(directory) / "video.mp4"),
                    )
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
