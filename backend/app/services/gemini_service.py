from __future__ import annotations

import json
from typing import Any

import requests

from app.core.config import settings


class GeminiService:
    def is_enabled(self) -> bool:
        return bool(settings.gemini_api_key)

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        content = self._generate_content(system_prompt, user_prompt)
        if not content:
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def chat_text(self, system_prompt: str, user_prompt: str) -> str | None:
        return self._generate_content(system_prompt, user_prompt)

    def _generate_content(self, system_prompt: str, user_prompt: str) -> str | None:
        if not self.is_enabled():
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        try:
            response = requests.post(
                url,
                headers={
                    "x-goog-api-key": settings.gemini_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "systemInstruction": {
                        "parts": [
                            {"text": system_prompt},
                        ]
                    },
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": user_prompt},
                            ],
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                    },
                },
                timeout=45,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            return None

        try:
            candidates = payload.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, AttributeError, TypeError):
            return None
