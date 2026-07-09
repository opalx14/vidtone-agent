from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


class FireworksClientError(RuntimeError):
    """Raised when the Fireworks API request fails."""


def _image_to_data_url(image_path: str | Path) -> str:
    """Encode a local image file as a data: URL suitable for the Fireworks
    chat completions API.

    Fireworks accepts the standard OpenAI-style vision payload where each
    image is a `data:<mime>;base64,<...>` URL inside an `image_url` message
    part.
    """
    path = Path(image_path)
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


@dataclass(frozen=True)
class FireworksClient:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int = 60

    # ------------------------------------------------------------------
    # Text-only completion (used by CaptionAgent and JudgeAgent).
    # ------------------------------------------------------------------
    def complete(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant.",
        temperature: float = 0.4,
        max_tokens: int = 400,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return self._post_and_extract(payload)

    # ------------------------------------------------------------------
    # Multimodal completion — one text prompt plus one or more images.
    # Used by VisionAgent to describe extracted keyframes.
    # ------------------------------------------------------------------
    def complete_multimodal(
        self,
        prompt: str,
        image_paths: list[str | Path],
        system_prompt: str = "You describe what is visually happening in short videos.",
        temperature: float = 0.2,
        max_tokens: int = 300,
    ) -> str:
        if not image_paths:
            raise FireworksClientError("complete_multimodal requires at least one image.")

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image_path in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": _image_to_data_url(image_path)},
                }
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return self._post_and_extract(payload)

    # ------------------------------------------------------------------
    # Shared HTTP + response parsing path.
    # ------------------------------------------------------------------
    def _post_and_extract(self, payload: dict[str, Any]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FireworksClientError(f"Fireworks API request failed: {exc}") from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise FireworksClientError(f"Unexpected Fireworks API response: {data}") from exc

        return str(content).strip()
