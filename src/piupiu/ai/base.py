from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


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
