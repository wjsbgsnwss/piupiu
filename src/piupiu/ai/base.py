from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    id: str
    type: str
    label: str
    properties: dict = field(default_factory=dict)


@dataclass
class Relationship:
    from_id: str
    to_id: str
    type: str
    properties: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    entities: list[Entity]
    relationships: list[Relationship]
    intent: str  # store | query | chat
    response: str


@runtime_checkable
class AIProvider(Protocol):
    async def process(self, message: str, context: list[dict]) -> ExtractionResult: ...


def parse_extraction(d: dict) -> ExtractionResult:
    """Build an ExtractionResult from a raw AI tool-call dict.

    Tolerates malformed items (strings, nulls, missing fields) that models
    occasionally produce instead of the expected object schema.
    """
    entities: list[Entity] = []
    for e in d.get("entities") or []:
        if not isinstance(e, dict):
            logger.warning("Skipping non-dict entity: %r", e)
            continue
        label = str(e.get("label") or e.get("id") or "").strip()
        if not label:
            continue
        entities.append(Entity(
            id=str(e.get("id") or label),
            type=str(e.get("type") or "Concept"),
            label=label,
            properties=e["properties"] if isinstance(e.get("properties"), dict) else {},
        ))

    relationships: list[Relationship] = []
    for r in d.get("relationships") or []:
        if not isinstance(r, dict):
            logger.warning("Skipping non-dict relationship: %r", r)
            continue
        from_id = str(r.get("from_id") or "").strip()
        to_id   = str(r.get("to_id")   or "").strip()
        if not from_id or not to_id:
            continue
        relationships.append(Relationship(
            from_id=from_id,
            to_id=to_id,
            type=str(r.get("type") or "RELATED_TO"),
            properties=r["properties"] if isinstance(r.get("properties"), dict) else {},
        ))

    return ExtractionResult(
        entities=entities,
        relationships=relationships,
        intent=str(d.get("intent") or "chat"),
        response=str(d.get("response") or ""),
    )
