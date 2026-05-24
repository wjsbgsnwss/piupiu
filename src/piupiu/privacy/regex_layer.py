from __future__ import annotations
import logging
import re
from .vault import Vault

logger = logging.getLogger(__name__)

# (type, pattern) — group 1 is the sensitive value when present
_PATTERNS: list[tuple[str, str]] = [
    ("connection_string",
     r"(?:mongodb|postgresql|mysql|sqlite|redis|amqp|rabbitmq)://[^\s\"'<>]+"),
    ("bearer_token",
     r"(?i)Bearer\s+([A-Za-z0-9\-._~+/]+=*)"),
    ("basic_auth_url",
     r"https?://[^:@\s]+:[^@\s]+@[^\s]+"),
    ("env_credential",
     r"(?i)(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|APIKEY|ACCESS_KEY|PRIVATE_KEY)"
     r"\s*[=:]\s*([^\s\"'\n,;]{4,})"),
    ("private_key_block",
     r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----[\s\S]+?"
     r"-----END (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
]

_COMPILED = [(t, re.compile(p)) for t, p in _PATTERNS]


class RegexLayer:
    """Fast pattern-matching layer for well-known secret formats."""

    async def redact(self, text: str, vault: Vault) -> str:
        for secret_type, pattern in _COMPILED:
            def _replace(m: re.Match, st: str = secret_type) -> str:
                # Use captured group when available; else the full match
                value = m.group(1) if m.lastindex else m.group(0)
                placeholder = vault.store(value, st)
                if m.lastindex:
                    return m.group(0).replace(value, placeholder, 1)
                return placeholder

            try:
                text = pattern.sub(_replace, text)
            except Exception as exc:
                logger.warning("RegexLayer pattern %s error: %s", secret_type, exc)
        return text
