"""Ollama transport tests without requiring a local model server."""

import json

from thief_agent.infra.ollama import ask_ollama


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"response": "A whispered escape."}).encode()


def test_ollama_posts_a_non_streaming_prompt(monkeypatch):
    seen = {}

    def urlopen(request, timeout):
        seen["payload"] = json.loads(request.data)
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    assert ask_ollama("answer", "system", "model-x", "http://ollama", 2.5) == (
        "A whispered escape."
    )
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["model"] == "model-x"
    assert seen["timeout"] == 2.5
