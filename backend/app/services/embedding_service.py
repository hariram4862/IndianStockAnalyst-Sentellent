from __future__ import annotations

import hashlib
import math

import requests

from app.core.config import settings


class EmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        if settings.gemini_api_key:
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/"
                    f"models/{settings.gemini_embedding_model}:embedContent"
                )
                response = requests.post(
                    url,
                    headers={
                        "x-goog-api-key": settings.gemini_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "content": {
                            "parts": [
                                {"text": text},
                            ]
                        },
                        "outputDimensionality": settings.embedding_dimensions,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                return payload["embedding"]["values"]
            except requests.RequestException:
                pass

        return self._deterministic_embedding(text, settings.embedding_dimensions)

    def _deterministic_embedding(self, text: str, dimensions: int) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < dimensions:
            for byte in digest:
                values.append((byte / 255.0) * 2 - 1)
                if len(values) == dimensions:
                    break
            digest = hashlib.sha256(digest).digest()

        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]
