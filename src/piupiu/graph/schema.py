from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    type: str
    label: str
    properties: dict = field(default_factory=dict)


@dataclass
class Edge:
    from_id: str
    to_id: str
    type: str
    properties: dict = field(default_factory=dict)


class NodeType:
    PERSON = "Person"
    CREDENTIAL = "Credential"
    RESOURCE = "Resource"
    SERVICE = "Service"
    ORGANIZATION = "Organization"
    CONCEPT = "Concept"
    EVENT = "Event"
    LOCATION = "Location"


class EdgeType:
    HAS_CREDENTIAL = "HAS_CREDENTIAL"
    GRANTS_ACCESS_TO = "GRANTS_ACCESS_TO"
    BELONGS_TO = "BELONGS_TO"
    KNOWS = "KNOWS"
    RELATED_TO = "RELATED_TO"
    USES = "USES"
    OWNS = "OWNS"
    WORKS_AT = "WORKS_AT"
