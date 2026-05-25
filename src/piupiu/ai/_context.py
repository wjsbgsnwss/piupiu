"""Shared graph context formatter for all AI providers."""


def format_context(context: list[dict]) -> str:
    """Render graph nodes as a readable block for the AI system prompt."""
    if not context:
        return ""

    lines: list[str] = []
    for n in context:
        line = f"- [{n['type']}] {n['label']}"

        props = {k: v for k, v in (n.get("properties") or {}).items() if v}
        if props:
            prop_str = "; ".join(f"{k}: {v}" for k, v in props.items())
            line += f" ({prop_str})"

        edges = n.get("edges") or []
        if edges:
            edge_parts = []
            for e in edges:
                if "to" in e:
                    edge_parts.append(f"{e['relation']} → {e['to']}")
                elif "from" in e:
                    edge_parts.append(f"{e['from']} → {e['relation']}")
            if edge_parts:
                line += " | " + ", ".join(edge_parts)

        lines.append(line)

    return "\n".join(lines)
