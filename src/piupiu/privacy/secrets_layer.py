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
        # Module renamed to high_entropy_strings (plural) in detect-secrets 1.4+
        from detect_secrets.plugins.high_entropy_strings import (
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

        # Load additional plugins introduced in v1.4+ if available
        _optional = [
            ("detect_secrets.plugins.openai", "OpenAIDetector"),
            ("detect_secrets.plugins.telegram_token", "TelegramTokenDetector"),
            ("detect_secrets.plugins.discord", "DiscordBotTokenDetector"),
            ("detect_secrets.plugins.npm", "NpmDetector"),
            ("detect_secrets.plugins.pypi_token", "PypiTokenDetector"),
        ]
        for module_path, cls_name in _optional:
            try:
                mod = __import__(module_path, fromlist=[cls_name])
                plugins.append(getattr(mod, cls_name)())
            except (ImportError, AttributeError):
                pass

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
