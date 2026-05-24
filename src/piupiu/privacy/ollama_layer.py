from __future__ import annotations
import json
import logging
import httpx
from .vault import Vault

logger = logging.getLogger(__name__)

_PROMPT = """\
You are a privacy filter. Your sole task: find sensitive data in the text below.

Look for: passwords, secrets, API keys, tokens, credentials, or personal identifiers \
that should not leave this machine.

Return a JSON array of findings — nothing else.
Each finding: {{"value": "<exact text>", "type": "password|api_key|pii|credential|other"}}
If nothing found, return: []

Text:
{text}

JSON:"""


class OllamaLayer:
    """Optional final privacy check using a locally running Ollama model.

    Catches contextual secrets that pattern-matching misses, e.g.
    'my password is the same as my cat's name, Whiskers'.
    Nothing ever leaves the machine.
    """

    def __init__(self, base_url: str, model: str, timeout: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def redact(self, text: str, vault: Vault) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": _PROMPT.format(text=text),
                        "stream": False,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "[]").strip()
                findings: list[dict] = json.loads(raw)

            for finding in findings:
                value = finding.get("value", "")
                ftype = finding.get("type", "sensitive")
                if value and value in text:
                    placeholder = vault.store(value, ftype)
                    text = text.replace(value, placeholder, 1)

        except json.JSONDecodeError:
            logger.warning("Ollama returned non-JSON — privacy check skipped for this message")
        except httpx.HTTPError as exc:
            logger.warning("Ollama unreachable: %s — skipping final privacy layer", exc)
        except Exception as exc:
            logger.warning("OllamaLayer error: %s", exc)

        return text
