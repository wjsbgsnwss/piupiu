from __future__ import annotations
from .presidio_layer import PresidioLayer
from .regex_layer import RegexLayer
from .secrets_layer import SecretsLayer
from .ollama_layer import OllamaLayer
from .vault import Vault


class PrivacyShield:
    """Four-layer redaction pipeline.

    Layer order:
      1. Presidio   — PII (names, emails, phones, IBANs …)
      2. detect-secrets — API keys, tokens, high-entropy strings
      3. Regex      — connection strings, .env credentials, bearer tokens
      4. Ollama     — optional local AI final check (contextual secrets)
    """

    def __init__(self, ollama: OllamaLayer | None = None) -> None:
        self._layers = [
            PresidioLayer(),
            SecretsLayer(),
            RegexLayer(),
        ]
        if ollama:
            self._layers.append(ollama)

    async def redact(self, text: str) -> tuple[str, Vault]:
        """Run all layers and return (redacted_text, vault_of_originals)."""
        vault = Vault()
        for layer in self._layers:
            text = await layer.redact(text, vault)
        return text, vault

    @classmethod
    def from_config(cls, cfg) -> "PrivacyShield":
        ollama = None
        if cfg.ollama_enabled:
            ollama = OllamaLayer(cfg.ollama_base_url, cfg.ollama_model, cfg.ollama_timeout)
        return cls(ollama=ollama)
