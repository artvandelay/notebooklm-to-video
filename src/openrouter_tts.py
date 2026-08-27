"""Resilient OpenRouter text-to-speech client."""

from __future__ import annotations

import math
import time

import requests


class OpenRouterTTSClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        session=None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = session if session is not None else requests.Session()
        self.last_generation_id = None

    def _sanitize(self, value: object) -> str:
        text = " ".join(str(value).split())
        if self.api_key:
            text = text.replace(self.api_key, "[REDACTED]")
        return text[:300]

    @staticmethod
    def _header(headers: object, name: str) -> str | None:
        if not hasattr(headers, "items"):
            return None
        for key, value in headers.items():
            if str(key).lower() == name.lower():
                return str(value)
        return None

    def _http_error(self, response) -> RuntimeError:
        status = getattr(response, "status_code", "unknown")
        excerpt = self._sanitize(getattr(response, "text", ""))
        return RuntimeError(f"OpenRouter TTS HTTP {status}: {excerpt}")

    def _validate_success(self, response) -> bytes:
        content = bytes(getattr(response, "content", b""))
        if not content:
            raise RuntimeError("OpenRouter TTS HTTP 200: empty response body")
        if len(content) % 2:
            raise RuntimeError("OpenRouter TTS HTTP 200: PCM body has odd byte length")
        content_type = self._header(getattr(response, "headers", {}), "Content-Type")
        normalized_type = (content_type or "").lower()
        if not (
            normalized_type.startswith("audio/")
            or normalized_type.startswith("application/octet-stream")
        ):
            excerpt = self._sanitize(getattr(response, "text", ""))
            raise RuntimeError(
                f"OpenRouter TTS HTTP 200: invalid Content-Type "
                f"{content_type!r}: {excerpt}"
            )
        if content.lstrip()[:1] in {b"{", b"<"}:
            excerpt = self._sanitize(getattr(response, "text", ""))
            raise RuntimeError(
                f"OpenRouter TTS HTTP 200: invalid non-audio body: {excerpt}"
            )
        self.last_generation_id = self._header(
            getattr(response, "headers", {}), "X-Generation-Id"
        )
        return content

    def synthesize(
        self, *, model: str, voice: str, text: str, timeout_s: int = 300
    ) -> bytes:
        url = f"{self.base_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "pcm",
        }
        self.last_generation_id = None

        for attempt in range(3):
            try:
                response = self.session.post(
                    url, headers=headers, json=payload, timeout=timeout_s
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == 2:
                    detail = self._sanitize(exc)
                    raise RuntimeError(
                        f"OpenRouter TTS transport error after 3 attempts: {detail}"
                    ) from exc
                time.sleep(2 ** (attempt + 1))
                continue

            status = response.status_code
            if status == 200:
                return self._validate_success(response)
            retryable = status == 429 or 500 <= status <= 599
            if not retryable or attempt == 2:
                raise self._http_error(response)

            delay = float(2 ** (attempt + 1))
            retry_after = self._header(
                getattr(response, "headers", {}), "Retry-After"
            )
            if retry_after is not None:
                try:
                    parsed_delay = float(retry_after)
                except ValueError:
                    pass
                else:
                    if math.isfinite(parsed_delay) and parsed_delay >= 0:
                        delay = max(delay, parsed_delay)
            time.sleep(delay)

        raise RuntimeError("OpenRouter TTS request failed")
