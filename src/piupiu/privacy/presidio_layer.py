from __future__ import annotations
import logging
from .vault import Vault

logger = logging.getLogger(__name__)


class PresidioLayer:
    """PII detection via Microsoft Presidio (optional dependency)."""

    def __init__(self) -> None:
        self._analyzer = None
        try:
            import spacy
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            # Pick whichever spacy model is already installed; never auto-download.
            for model in ("en_core_web_sm", "en_core_web_md", "en_core_web_lg"):
                if spacy.util.is_package(model):
                    provider = NlpEngineProvider(nlp_configuration={
                        "nlp_engine_name": "spacy",
                        "models": [{"lang_code": "en", "model_name": model}],
                    })
                    self._analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
                    logger.debug("Presidio analyzer loaded with model %s", model)
                    break
            if self._analyzer is None:
                logger.warning(
                    "No spacy model found — Presidio PII layer skipped. "
                    "Run: python3 -m spacy download en_core_web_sm"
                )
        except ImportError:
            logger.warning("presidio-analyzer not installed — PII detection layer skipped")

    async def redact(self, text: str, vault: Vault) -> str:
        if self._analyzer is None:
            return text
        try:
            results = self._analyzer.analyze(text=text, language="en")
            # Replace from right to left so offsets stay valid
            for r in sorted(results, key=lambda x: x.start, reverse=True):
                original = text[r.start:r.end]
                placeholder = vault.store(original, r.entity_type.lower())
                text = text[:r.start] + placeholder + text[r.end:]
        except Exception as exc:
            logger.warning("Presidio error: %s", exc)
        return text
