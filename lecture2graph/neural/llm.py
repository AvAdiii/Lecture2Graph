"""
Local LLM client — OpenAI-compatible chat, no API key, no cloud.

The neural extractor talks to a *local* model server through the standard
OpenAI `/v1/chat/completions` interface, which Ollama (default), LM Studio,
llama.cpp-server and vLLM all expose. Nothing here is provider-specific, and
there is no SDK dependency — it is a thin stdlib (`urllib`) POST.

Configure via environment (defaults target Ollama):

    LECTURE2GRAPH_LLM_BASE_URL   default http://localhost:11434/v1
    LECTURE2GRAPH_LLM_MODEL      default llama3.1:8b
    LECTURE2GRAPH_LLM_API_KEY    default "ollama"  (ignored by local servers)

Run a model first, e.g.:  `ollama pull llama3.1:8b && ollama serve`
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.1:8b"

_MAX_RETRIES = 3
_TIMEOUT = 600  # local models can be slow; generous ceiling


def base_url() -> str:
    return os.environ.get("LECTURE2GRAPH_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def model() -> str:
    return os.environ.get("LECTURE2GRAPH_LLM_MODEL", DEFAULT_MODEL)


def api_key() -> str:
    return os.environ.get("LECTURE2GRAPH_LLM_API_KEY", "ollama")


def _post(system: str, user: str, temperature: float,
          max_tokens: int | None, json_mode: bool) -> str:
    payload: dict = {
        "model": model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "stream": False,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{base_url()}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key()}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        body = json.loads(resp.read().decode())
    return body["choices"][0]["message"]["content"]


def chat(system: str, user: str, *, temperature: float = 0.1,
         json_mode: bool = True, max_tokens: int | None = 8000) -> str:
    """Send a system+user prompt to the local model and return the reply text.

    Retries transient failures. If the server rejects `response_format` (older
    builds), it transparently retries without JSON mode. Raises a clear
    ConnectionError if no local server is reachable.
    """
    use_json = json_mode
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            return _post(system, user, temperature, max_tokens, use_json)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="ignore")
            if use_json and ("response_format" in detail or e.code == 400):
                use_json = False  # server lacks JSON mode — drop it and retry
                continue
            last_err = f"HTTP {e.code}: {detail[:200]}"
            time.sleep(2 * (attempt + 1))
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot reach a local LLM at {base_url()} — is the server "
                f"running?  (e.g. `ollama serve`)  Underlying error: {e.reason}"
            ) from e
    raise RuntimeError(f"Local LLM call failed after {_MAX_RETRIES} tries: {last_err}")


def extract_json(text: str) -> dict:
    """Robustly pull a JSON object out of a model reply (handles fences/prose)."""
    import re

    t = re.sub(r"^```(?:json)?\s*", "", text.strip())
    t = re.sub(r"\s*```$", "", t.strip())
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # fall back to the outermost {...}
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(t[start:end + 1])
        raise
