from app.core.config import settings
from app.services.gemini_service import GeminiService


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _fake_success_payload(text: str = "ok") -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_chat_text_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    service = GeminiService()
    assert service.chat_text("system", "hello") is None


def test_chat_text_sends_single_turn_when_no_history(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _FakeResponse(_fake_success_payload("hi there"))

    monkeypatch.setattr("app.services.gemini_service.requests.post", fake_post)

    result = GeminiService().chat_text("system prompt", "What's the sentiment on TCS?")

    assert result == "hi there"
    assert captured["json"]["contents"] == [
        {"role": "user", "parts": [{"text": "What's the sentiment on TCS?"}]}
    ]


def test_chat_text_threads_history_as_multi_turn_contents(monkeypatch):
    """The whole point of passing `history` is that it becomes real prior
    turns in the Gemini request (assistant -> "model" role), not text
    stuffed into the single user prompt -- this is what actually gives the
    agent multi-turn conversational memory."""
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _FakeResponse(_fake_success_payload("continuing the thread"))

    monkeypatch.setattr("app.services.gemini_service.requests.post", fake_post)

    history = [
        ("user", "What's the sentiment on TCS this week?"),
        ("assistant", "TCS sentiment is positive per [1]."),
    ]
    result = GeminiService().chat_text("system prompt", "What about its debt?", history=history)

    assert result == "continuing the thread"
    contents = captured["json"]["contents"]
    assert contents == [
        {"role": "user", "parts": [{"text": "What's the sentiment on TCS this week?"}]},
        {"role": "model", "parts": [{"text": "TCS sentiment is positive per [1]."}]},
        {"role": "user", "parts": [{"text": "What about its debt?"}]},
    ]


def test_chat_json_parses_model_output(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(
        "app.services.gemini_service.requests.post",
        lambda url, headers, json, timeout: _FakeResponse(_fake_success_payload('{"risk_profile": "conservative"}')),
    )
    result = GeminiService().chat_json("system", "user")
    assert result == {"risk_profile": "conservative"}
