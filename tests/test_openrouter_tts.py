import unittest
from unittest.mock import patch

import requests

from src.openrouter_tts import OpenRouterTTSClient


class FakeResponse:
    def __init__(self, status_code, content=b"", headers=None, text=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content.decode("utf-8", errors="replace") if text is None else text


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def pcm_response(content=b"\x01\x00", headers=None):
    response_headers = {"Content-Type": "audio/L16"}
    if headers:
        response_headers.update(headers)
    return FakeResponse(200, content=content, headers=response_headers)


class OpenRouterTTSClientTests(unittest.TestCase):
    def test_posts_exact_endpoint_payload_and_headers(self):
        session = FakeSession(
            [pcm_response(headers={"X-Generation-Id": "generation-123"})]
        )
        client = OpenRouterTTSClient(
            "secret-key", base_url="https://example.test/api/v1/", session=session
        )

        result = client.synthesize(
            model="tts-model", voice="Kore", text="Hello", timeout_s=42
        )

        self.assertEqual(result, b"\x01\x00")
        self.assertEqual(client.last_generation_id, "generation-123")
        self.assertEqual(len(session.calls), 1)
        url, kwargs = session.calls[0]
        self.assertEqual(url, "https://example.test/api/v1/audio/speech")
        self.assertEqual(
            kwargs["headers"],
            {
                "Authorization": "Bearer secret-key",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(
            kwargs["json"],
            {
                "model": "tts-model",
                "input": "Hello",
                "voice": "Kore",
                "response_format": "pcm",
            },
        )
        self.assertEqual(kwargs["timeout"], 42)

    def test_accepts_octet_stream_pcm_and_case_insensitive_headers(self):
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    content=b"\xff\x7f\x00\x80",
                    headers={
                        "content-type": "application/octet-stream; charset=binary",
                        "x-generation-id": "case-insensitive",
                    },
                )
            ]
        )
        client = OpenRouterTTSClient("key", session=session)

        self.assertEqual(
            client.synthesize(model="model", voice="voice", text="text"),
            b"\xff\x7f\x00\x80",
        )
        self.assertEqual(client.last_generation_id, "case-insensitive")

    def test_retries_429_then_succeeds_and_honors_retry_after(self):
        session = FakeSession(
            [
                FakeResponse(
                    429,
                    content=b"rate limited",
                    headers={"Retry-After": "3.5"},
                ),
                pcm_response(),
            ]
        )
        client = OpenRouterTTSClient("key", session=session)

        with patch("src.openrouter_tts.time.sleep") as sleep:
            result = client.synthesize(model="model", voice="voice", text="text")

        self.assertEqual(result, b"\x01\x00")
        sleep.assert_called_once_with(3.5)
        self.assertEqual(len(session.calls), 2)

    def test_does_not_retry_400_and_sanitizes_error(self):
        key = "do-not-leak-this"
        response_text = f"bad request containing {key} " + ("x" * 400)
        session = FakeSession(
            [FakeResponse(400, content=b"bad request", text=response_text)]
        )
        client = OpenRouterTTSClient(key, session=session)

        with patch("src.openrouter_tts.time.sleep") as sleep:
            with self.assertRaises(RuntimeError) as context:
                client.synthesize(model="model", voice="voice", text="text")

        message = str(context.exception)
        self.assertIn("HTTP 400", message)
        self.assertNotIn(key, message)
        self.assertLessEqual(len(message.partition(": ")[2]), 300)
        self.assertEqual(len(session.calls), 1)
        sleep.assert_not_called()

    def test_rejects_odd_pcm_body(self):
        client = OpenRouterTTSClient(
            "key", session=FakeSession([pcm_response(b"\x00")])
        )

        with self.assertRaisesRegex(RuntimeError, "odd byte length"):
            client.synthesize(model="model", voice="voice", text="text")

    def test_rejects_json_and_html_bodies(self):
        for body in (b'  {"error":"not audio"} ', b"\n<html></html> "):
            with self.subTest(body=body):
                if len(body) % 2:
                    body += b" "
                client = OpenRouterTTSClient(
                    "key", session=FakeSession([pcm_response(body)])
                )
                with self.assertRaisesRegex(RuntimeError, "non-audio body"):
                    client.synthesize(model="model", voice="voice", text="text")

    def test_rejects_empty_body_and_invalid_content_type(self):
        responses = [
            (pcm_response(b""), "empty response body"),
            (
                FakeResponse(
                    200,
                    content=b"\x00\x00",
                    headers={"Content-Type": "application/json"},
                ),
                "invalid Content-Type",
            ),
        ]
        for response, message in responses:
            with self.subTest(message=message):
                client = OpenRouterTTSClient(
                    "key", session=FakeSession([response])
                )
                with self.assertRaisesRegex(RuntimeError, message):
                    client.synthesize(model="model", voice="voice", text="text")

    def test_retries_transport_errors_twice_then_exhausts(self):
        key = "transport-secret"
        session = FakeSession(
            [
                requests.Timeout("first"),
                requests.ConnectionError("second"),
                requests.Timeout(f"third {key}"),
            ]
        )
        client = OpenRouterTTSClient(key, session=session)

        with patch("src.openrouter_tts.time.sleep") as sleep:
            with self.assertRaises(RuntimeError) as context:
                client.synthesize(model="model", voice="voice", text="text")

        self.assertIn("after 3 attempts", str(context.exception))
        self.assertNotIn(key, str(context.exception))
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])
        self.assertEqual(len(session.calls), 3)

    def test_retries_server_errors_at_most_three_total_attempts(self):
        session = FakeSession(
            [
                FakeResponse(500, text="one"),
                FakeResponse(503, text="two"),
                FakeResponse(599, text="three"),
            ]
        )
        client = OpenRouterTTSClient("key", session=session)

        with patch("src.openrouter_tts.time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 599"):
                client.synthesize(model="model", voice="voice", text="text")

        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2.0, 4.0])
        self.assertEqual(len(session.calls), 3)


if __name__ == "__main__":
    unittest.main()
