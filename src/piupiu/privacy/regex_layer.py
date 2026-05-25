from __future__ import annotations
import logging
import re
from .vault import Vault

logger = logging.getLogger(__name__)

# (type, pattern)
# Patterns with capture groups: the first non-None group is the secret value.
# Patterns without groups: the full match is the secret value.
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
    # Natural language: "password is 'val'", "password is "val"", "password is val"
    # Lazy (.+?) expands until the closing quote is followed by whitespace/punct/end,
    # so embedded quotes inside the value are handled correctly.
    ("natural_language_credential",
     r"(?i)(?:password|passwd|secret|api.?key|token|passphrase)\s+is\s+"
     r"(?:'(.+?)'(?=[\s,;.]|$)|\"(.+?)\"(?=[\s,;.]|$)|([^'\"\s,;]{8,}))"),
    ("private_key_block",
     r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----[\s\S]+?"
     r"-----END (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
]

_COMPILED = [(t, re.compile(p)) for t, p in _PATTERNS]


def _first_group(m: re.Match) -> str:
    """Return the first non-None capture group, or the full match if none."""
    return next(
        (m.group(i) for i in range(1, (m.lastindex or 0) + 1) if m.group(i) is not None),
        m.group(0),
    )


class RegexLayer:
    """Fast pattern-matching layer for well-known secret formats."""

    async def redact(self, text: str, vault: Vault) -> str:
        for secret_type, pattern in _COMPILED:
            def _replace(m: re.Match, st: str = secret_type) -> str:
                value = _first_group(m)
                placeholder = vault.store(value, st)
                full = m.group(0)
                return full.replace(value, placeholder, 1) if value != full else placeholder

            try:
                text = pattern.sub(_replace, text)
            except Exception as exc:
                logger.warning("RegexLayer pattern %s error: %s", secret_type, exc)
        return text
