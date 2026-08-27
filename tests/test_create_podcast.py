import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import create_podcast


def make_config(slug="sample-episode", turn_texts=("Welcome.", "Thank you.")):
    return SimpleNamespace(
        episode=SimpleNamespace(
            slug=slug,
            title="Sample Episode",
            summary="A concise summary.",
            art_prompt="Show the hosts discussing the named subject.",
        ),
        turns=tuple(SimpleNamespace(text=text) for text in turn_texts),
    )


def make_rendered(job_dir):
    return SimpleNamespace(
        wav_path=job_dir / "sample-episode.podcast.wav",
        mp3_path=job_dir / "sample-episode.podcast.mp3",
        manifest_path=job_dir / ".podcast" / "manifest.json",
        timings=("timing",),
    )


class CreatePodcastTests(unittest.TestCase):
    def pipeline_patches(self, job_dir, config=None):
        config = config or make_config()
        rendered = make_rendered(job_dir)
        patchers = (
            patch.object(
                create_podcast,
                "resolve_podcast_config",
                return_value=job_dir / "podcast.json",
            ),
            patch.object(create_podcast, "load_podcast_config", return_value=config),
            patch.object(create_podcast, "load_dotenv"),
            patch.object(create_podcast.os, "getenv", return_value="test-key"),
            patch.object(create_podcast, "OpenRouterTTSClient"),
            patch.object(create_podcast, "render_podcast", return_value=rendered),
            patch.object(create_podcast, "generate_cover_art"),
            patch.object(create_podcast, "create_video"),
            patch.object(create_podcast, "render_youtube_package"),
        )
        mocks = tuple(patcher.start() for patcher in patchers)
        for patcher in reversed(patchers):
            self.addCleanup(patcher.stop)
        return (config, rendered, *mocks)

    def test_successful_pipeline_uses_canonical_paths_and_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            job_dir = Path(temporary_dir)
            (
                config,
                rendered,
                resolve,
                load,
                dotenv,
                getenv,
                client_class,
                render,
                generate,
                video,
                youtube,
            ) = self.pipeline_patches(job_dir)

            outputs = create_podcast.run_pipeline(
                "input-folder",
                force_audio=True,
                force_art=True,
                auto_approve=True,
            )

            resolve.assert_called_once_with("input-folder")
            load.assert_called_once_with(job_dir / "podcast.json")
            client_class.assert_called_once_with("test-key")
            render.assert_called_once_with(
                config, job_dir, client_class.return_value, force=True
            )
            transcript = "Welcome.\nThank you."
            generate.assert_called_once_with(
                transcript,
                output_dir=str(job_dir),
                output_path=job_dir / "sample-episode.png",
                prompt_override=(
                    "Episode title: Sample Episode\n"
                    "Summary: A concise summary.\n"
                    "Art prompt: Show the hosts discussing the named subject.\n"
                    f"Transcript excerpt: {transcript}"
                ),
            )
            video.assert_called_once_with(
                str(job_dir / "sample-episode.png"),
                str(rendered.mp3_path),
                str(job_dir / "sample-episode_video.mp4"),
                resolution=(1920, 1080),
            )
            youtube.assert_called_once_with(
                config,
                rendered.timings,
                job_dir / "sample-episode.youtube.md",
            )
            self.assertEqual(outputs["cover"], job_dir / "sample-episode.png")
            self.assertEqual(outputs["video"], job_dir / "sample-episode_video.mp4")
            self.assertEqual(
                outputs["youtube"], job_dir / "sample-episode.youtube.md"
            )

    def test_external_calls_are_ordered_audio_art_video_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            job_dir = Path(temporary_dir)
            events = []
            patches = self.pipeline_patches(job_dir)
            (
                _,
                _,
                resolve,
                load,
                dotenv,
                getenv,
                client_class,
                render,
                generate,
                video,
                youtube,
            ) = patches
            render.side_effect = lambda *args, **kwargs: (
                events.append("audio") or make_rendered(job_dir)
            )
            generate.side_effect = lambda *args, **kwargs: events.append("art")
            video.side_effect = lambda *args, **kwargs: events.append("video")
            youtube.side_effect = lambda *args, **kwargs: events.append("metadata")

            create_podcast.run_pipeline("input", force_art=True, auto_approve=True)

            self.assertEqual(events, ["audio", "art", "video", "metadata"])

    def test_loads_root_dotenv_path(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            job_dir = Path(temporary_dir)
            patches = self.pipeline_patches(job_dir)
            (_, _, resolve, load, dotenv, getenv, client, render, art, video, youtube) = (
                patches
            )
            create_podcast.run_pipeline("input", force_art=True, auto_approve=True)

            dotenv.assert_called_once_with(
                Path(create_podcast.__file__).resolve().parent / ".env"
            )

    def test_missing_api_key_fails_before_client_creation(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            job_dir = Path(temporary_dir)
            with (
                patch.object(
                    create_podcast,
                    "resolve_podcast_config",
                    return_value=job_dir / "podcast.json",
                ),
                patch.object(
                    create_podcast, "load_podcast_config", return_value=make_config()
                ),
                patch.object(create_podcast, "load_dotenv"),
                patch.object(create_podcast.os, "getenv", return_value=None),
                patch.object(create_podcast, "OpenRouterTTSClient") as client,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "OPENROUTER_API_KEY is required"
                ):
                    create_podcast.run_pipeline("input", auto_approve=True)
            client.assert_not_called()

    def test_cancellation_returns_zero_without_video_or_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            job_dir = Path(temporary_dir)
            patches = self.pipeline_patches(job_dir)
            (_, _, resolve, load, dotenv, getenv, client, render, art, video, youtube) = (
                patches
            )
            with (
                patch("builtins.input", return_value="n") as user_input,
            ):
                result = create_podcast.main(["input", "--force-art"])

            self.assertEqual(result, 0)
            user_input.assert_called_once_with(
                "Proceed with video creation? (y/n): "
            )
            video.assert_not_called()
            youtube.assert_not_called()

    def test_supplied_cover_is_copied_atomically_to_canonical_path(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            job_dir = root / "episode"
            job_dir.mkdir()
            source = root / "provided.png"
            source.write_bytes(b"png-data")
            patches = self.pipeline_patches(job_dir)
            (_, _, resolve, load, dotenv, getenv, client, render, art, video, youtube) = (
                patches
            )

            with (
                patch.object(create_podcast.shutil, "copy2", wraps=create_podcast.shutil.copy2) as copy,
                patch.object(create_podcast.os, "replace", wraps=create_podcast.os.replace) as replace,
            ):
                create_podcast.run_pipeline(
                    "input", cover_art_path=source, auto_approve=True
                )

            canonical = job_dir / "sample-episode.png"
            self.assertEqual(canonical.read_bytes(), b"png-data")
            copy.assert_called_once_with(source.resolve(), canonical.with_name(f"{canonical.name}.tmp"))
            replace.assert_called_once_with(
                canonical.with_name(f"{canonical.name}.tmp"), canonical
            )
            art.assert_not_called()

    def test_main_forwards_parser_arguments(self):
        expected = {"video": Path("video.mp4")}
        with patch.object(
            create_podcast, "run_pipeline", return_value=expected
        ) as pipeline:
            result = create_podcast.main(
                [
                    "uploads/example",
                    "--cover-art",
                    "cover.png",
                    "--force-audio",
                    "--force-art",
                    "--auto-approve",
                ]
            )

        self.assertEqual(result, 0)
        pipeline.assert_called_once_with(
            "uploads/example",
            cover_art_path="cover.png",
            force_audio=True,
            force_art=True,
            auto_approve=True,
        )

    def test_main_prints_error_and_returns_nonzero(self):
        with (
            patch.object(
                create_podcast,
                "run_pipeline",
                side_effect=ValueError("invalid config"),
            ),
            patch("sys.stderr") as stderr,
        ):
            result = create_podcast.main(["uploads/example"])

        self.assertEqual(result, 1)
        self.assertEqual(
            stderr.method_calls,
            [call.write("Error: invalid config"), call.write("\n")],
        )

    def test_art_prompt_limits_joined_turn_excerpt_to_1200_characters(self):
        transcript = "a" * 800 + "\n" + "b" * 800
        prompt = create_podcast._art_prompt(make_config(), transcript)
        self.assertTrue(prompt.endswith(transcript[:1200]))
        self.assertNotIn("b" * 401, prompt)


if __name__ == "__main__":
    unittest.main()
