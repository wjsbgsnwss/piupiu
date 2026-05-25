SYSTEM_PROMPT = """\
You are PiuPiu, a private knowledge graph assistant.
You help users remember and recall personal information — credentials, contacts, \
resources, notes — all stored privately on their own machine.

Rules:
- Extract entities and relationships from every message.
- Placeholders like <SECRET:type:uid> represent sensitive values the user shared.
  Preserve them exactly in entity labels and properties — never expand or guess their content.
- Set intent to "store" when the user is sharing information,
  "query" when asking a question, "chat" for everything else.
- Use graph context (when provided) to give accurate, specific answers.
- Be concise and friendly. Do not use markdown formatting in responses.
- CRITICAL: In your "response" field, NEVER write placeholder syntax like <SECRET:...>.
  Always output the actual plaintext values from the graph context directly.
  The user wants to see their real data, not internal tokens.
"""

# Anthropic tool format (input_schema key)
PROCESS_TOOL = {
    "name": "process_message",
    "description": "Extract knowledge from the message and produce a response.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Stable snake_case ID"},
                        "type": {
                            "type": "string",
                            "description": (
                                "Person | Credential | Resource | Service | "
                                "Organization | Concept | Event | Location"
                            ),
                        },
                        "label": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["id", "type", "label"],
                },
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "from_id": {"type": "string"},
                        "to_id": {"type": "string"},
                        "type": {"type": "string", "description": "USES | OWNS | KNOWS | HAS_CREDENTIAL | GRANTS_ACCESS_TO | BELONGS_TO | RELATED_TO"},
                        "properties": {"type": "object"},
                    },
                    "required": ["from_id", "to_id", "type"],
                },
            },
            "intent": {
                "type": "string",
                "enum": ["store", "query", "chat"],
            },
            "response": {
                "type": "string",
                "description": "Natural language reply to send back to the user.",
            },
        },
        "required": ["entities", "relationships", "intent", "response"],
    },
}

# OpenAI-compatible tool format (used by NIM and other OpenAI-compatible providers)
_SCHEMA = PROCESS_TOOL["input_schema"]  # reuse the same schema
PROCESS_TOOL_OPENAI = {
    "type": "function",
    "function": {
        "name": PROCESS_TOOL["name"],
        "description": PROCESS_TOOL["description"],
        "parameters": _SCHEMA,
    },
}
