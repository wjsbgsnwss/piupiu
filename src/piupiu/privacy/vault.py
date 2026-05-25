import logging
import re
import uuid
from dataclasses import dataclass, field

PLACEHOLDER_RE = re.compile(r"<SECRET:([^:>]+):([0-9a-f]{8})>")

logger = logging.getLogger(__name__)


@dataclass
class Vault:
    """Maps placeholder IDs to (type, original_value) pairs."""

    _store: dict[str, tuple[str, str]] = field(default_factory=dict)

    def store(self, original: str, secret_type: str) -> str:
        """Redact *original*, return a typed placeholder."""
        uid = uuid.uuid4().hex[:8]
        self._store[uid] = (secret_type, original)
        placeholder = f"<SECRET:{secret_type}:{uid}>"
        logger.debug("Redacted [%s]: %r  →  %s", secret_type, original, placeholder)
        return placeholder

    def restore_all(self, text: str) -> str:
        """Replace all placeholders in *text* with their originals."""
        def _sub(m: re.Match) -> str:
            entry = self._store.get(m.group(2))
            return entry[1] if entry else m.group(0)

        return PLACEHOLDER_RE.sub(_sub, text)

    def get_original(self, uid: str) -> str | None:
        entry = self._store.get(uid)
        return entry[1] if entry else None

    def merge(self, other: "Vault") -> None:
        self._store.update(other._store)

    def to_dict(self) -> dict:
        return dict(self._store)

    @classmethod
    def from_dict(cls, data: dict) -> "Vault":
        v = cls()
        v._store = {k: tuple(v) for k, v in data.items()}  # type: ignore[arg-type]
        return v
