from __future__ import annotations
import logging
from .vault import Vault

logger = logging.getLogger(__name__)


def _load_plugins() -> list:
    plugins: list = []
    try:
        from detect_secrets.plugins.aws import AWSKeyDetector
        from detect_secrets.plugins.basic_auth import BasicAuthDetector
        from detect_secrets.plugins.github_token import GitHubTokenDetector
        from detect_secrets.plugins.jwt import JwtTokenDetector
        from detect_secrets.plugins.private_key import PrivateKeyDetector
        from detect_secrets.plugins.slack import SlackDetector
        from detect_secrets.plugins.stripe import StripeDetector
        from detect_secrets.plugins.high_entropy_string import (
            HexHighEntropyString,
            Base64HighEntropyString,
        )

        plugins = [
            AWSKeyDetector(),
            BasicAuthDetector(),
            GitHubTokenDetector(),
            JwtTokenDetector(),
            PrivateKeyDetector(),
            SlackDetector(),
            StripeDetector(),
            HexHighEntropyString(limit=3.0),
            Base64HighEntropyString(limit=4.5),
        ]
        logger.debug("detect-secrets plugins loaded (%d)", len(plugins))
    except ImportError as exc:
        logger.warning("detect-secrets not available: %s — token detection layer skipped", exc)
    return plugins


class SecretsLayer:
    """Token/credential detection via Yelp detect-secrets (optional dependency)."""

    def __init__(self) -> None:
        self._plugins = _load_plugins()

    async def redact(self, text: str, vault: Vault) -> str:
        if not self._plugins:
            return text
        lines = text.split("\n")
        for lineno, line in enumerate(lines, 1):
            for plugin in self._plugins:
                try:
                    for secret in plugin.analyze_line(line, lineno):
                        value = getattr(secret, "secret_value", None)
                        if value and value in line:
                            stype = getattr(secret, "type", "secret").lower().replace(" ", "_")
                            placeholder = vault.store(value, stype)
                            line = line.replace(value, placeholder, 1)
                except Exception:
                    pass
            lines[lineno - 1] = line
        return "\n".join(lines)
