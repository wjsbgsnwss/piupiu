from __future__ import annotations
import logging
import re

import networkx as nx

from .schema import Edge, Node
from .storage import GraphStorage
from ..privacy.vault import Vault

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class GraphEngine:
    """In-memory NetworkX graph backed by encrypted storage."""

    def __init__(self, storage: GraphStorage) -> None:
        self._storage = storage
        self._graph: nx.DiGraph = storage.load_graph()
        self._persistent_vault = Vault.from_dict(storage.load_vault_data())
        self._id_map: dict[str, str] = {}
        removed = self._deduplicate()
        if removed:
            logger.info("Startup dedup: merged %d duplicate node(s) — persisting clean graph", removed)
            self._storage.save_graph(self._graph)
        logger.info("Graph loaded: %s", self.stats())

    # ── write ─────────────────────────────────────────────────────────────

    @staticmethod
    def _canonical_id(node_type: str, label: str) -> str:
        """Stable, deterministic node ID: '<type_slug>:<label_slug>'."""
        t = _SLUG_RE.sub("_", node_type.strip().lower()).strip("_") or "node"
        l = _SLUG_RE.sub("_", label.strip().lower()).strip("_") or "unknown"
        return f"{t}:{l}"

    def upsert_node(self, node: Node, session_vault: Vault) -> str:
        """Merge node into the graph under its canonical ID; return that ID."""
        label = self._restore(node.label, session_vault)
        props = {k: self._restore(str(v), session_vault) for k, v in node.properties.items()}
        canonical = self._canonical_id(node.type, label)

        if self._graph.has_node(canonical):
            # Merge: fill missing attributes with new values, keep existing ones
            existing = self._graph.nodes[canonical]
            for k, v in props.items():
                if v and k not in existing:
                    existing[k] = v
            existing["type"] = node.type
            existing["label"] = label
        else:
            self._graph.add_node(canonical, type=node.type, label=label, **props)

        self._id_map[node.id] = canonical
        self._persistent_vault.merge(session_vault)
        return canonical

    def upsert_edge(self, edge: Edge, session_vault: Vault) -> None:
        from_id = self._id_map.get(edge.from_id, edge.from_id)
        to_id = self._id_map.get(edge.to_id, edge.to_id)

        if not self._graph.has_node(from_id) or not self._graph.has_node(to_id):
            logger.debug("Skipping edge %s→%s: node(s) missing", from_id, to_id)
            return

        # Deduplicate: skip if same-type edge already exists between these nodes
        if self._graph.has_edge(from_id, to_id):
            if (self._graph.get_edge_data(from_id, to_id) or {}).get("type") == edge.type:
                return

        props = {k: self._restore(str(v), session_vault) for k, v in edge.properties.items()}
        self._graph.add_edge(from_id, to_id, type=edge.type, **props)

    # ── read ──────────────────────────────────────────────────────────────

    def get_context(self, query: str, max_nodes: int = 20) -> list[dict]:
        """Return graph nodes whose label overlaps with query terms."""
        words = set(query.lower().split())
        results: list[dict] = []
        for node_id, data in self._graph.nodes(data=True):
            label = data.get("label", "").lower()
            if words & set(label.split()):
                edges = []
                for nb in list(self._graph.successors(node_id))[:5]:
                    edge_data = self._graph.get_edge_data(node_id, nb) or {}
                    nb_label = self._graph.nodes[nb].get("label", nb)
                    edges.append({"to": nb_label, "relation": edge_data.get("type", "RELATED_TO")})
                for nb in list(self._graph.predecessors(node_id))[:5]:
                    edge_data = self._graph.get_edge_data(nb, node_id) or {}
                    nb_label = self._graph.nodes[nb].get("label", nb)
                    edges.append({"from": nb_label, "relation": edge_data.get("type", "RELATED_TO")})
                results.append({
                    "id": node_id,
                    "type": data.get("type"),
                    "label": data.get("label"),
                    "properties": {k: v for k, v in data.items() if k not in ("type", "label")},
                    "edges": edges,
                })
                if len(results) >= max_nodes:
                    break
        return results

    def dump(self) -> str:
        """Return a human-readable summary of every node and edge in the graph."""
        if self._graph.number_of_nodes() == 0:
            return "Graph is empty — tell me something to remember!"

        lines: list[str] = [
            f"Graph: {self._graph.number_of_nodes()} nodes, "
            f"{self._graph.number_of_edges()} edges",
            "",
            "Nodes:",
        ]

        for node_id, data in self._graph.nodes(data=True):
            ntype = data.get("type", "?")
            label = data.get("label", node_id)
            props = {k: v for k, v in data.items() if k not in ("type", "label")}
            prop_str = f"  ({'; '.join(f'{k}: {v}' for k, v in props.items())})" if props else ""
            lines.append(f"  [{ntype}]  {label}{prop_str}")

        lines += ["", "Edges:"]
        for src, dst, data in self._graph.edges(data=True):
            src_label = self._graph.nodes[src].get("label", src)
            dst_label = self._graph.nodes[dst].get("label", dst)
            rel = data.get("type", "RELATED_TO")
            lines.append(f"  {src_label}  ──{rel}──►  {dst_label}")

        return "\n".join(lines)

    def restore(self, text: str) -> str:
        """Replace any vault placeholders in text with their original values."""
        return self._persistent_vault.restore_all(text)

    def stats(self) -> dict:
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
        }

    # ── deduplication ─────────────────────────────────────────────────────

    def _deduplicate(self) -> int:
        """Normalise all node IDs to canonical form, merging duplicates in place.

        Returns the number of duplicate nodes that were eliminated.
        """
        from collections import defaultdict
        groups: dict[str, list[str]] = defaultdict(list)
        for node_id, data in list(self._graph.nodes(data=True)):
            key = self._canonical_id(
                data.get("type", ""), data.get("label", str(node_id))
            )
            groups[key].append(node_id)

        rename_map: dict[str, str] = {}
        removed = 0

        for canonical, node_ids in groups.items():
            # Use existing canonical node as primary; fall back to first in list
            primary = canonical if canonical in node_ids else node_ids[0]

            # Merge all duplicates into primary
            for dup_id in node_ids:
                if dup_id == primary:
                    continue
                self._merge_into(dup_id, primary)
                removed += 1

            # Schedule primary → canonical rename (no-op when primary == canonical)
            if primary != canonical:
                rename_map[primary] = canonical

        if rename_map:
            nx.relabel_nodes(self._graph, rename_map, copy=False)

        return removed

    def _merge_into(self, dup_id: str, primary_id: str) -> None:
        """Copy dup_id's missing attributes and edges into primary_id, then remove it."""
        dup_attrs = dict(self._graph.nodes[dup_id])
        primary_attrs = self._graph.nodes[primary_id]
        for k, v in dup_attrs.items():
            if v and k not in primary_attrs:
                primary_attrs[k] = v

        for pred in list(self._graph.predecessors(dup_id)):
            if pred == dup_id or pred == primary_id:
                continue  # skip self-loops
            edge_data = dict(self._graph.get_edge_data(pred, dup_id) or {})
            if not self._graph.has_edge(pred, primary_id):
                self._graph.add_edge(pred, primary_id, **edge_data)

        for succ in list(self._graph.successors(dup_id)):
            if succ == dup_id or succ == primary_id:
                continue  # skip self-loops
            edge_data = dict(self._graph.get_edge_data(dup_id, succ) or {})
            if not self._graph.has_edge(primary_id, succ):
                self._graph.add_edge(primary_id, succ, **edge_data)

        self._graph.remove_node(dup_id)

    # ── persistence ───────────────────────────────────────────────────────

    def persist(self) -> None:
        self._storage.save_graph(self._graph)
        self._storage.save_vault_data(self._persistent_vault.to_dict())
        logger.debug("Graph persisted: %s", self.stats())

    # ── helpers ───────────────────────────────────────────────────────────

    def _restore(self, text: str, session_vault: Vault) -> str:
        text = session_vault.restore_all(text)
        return self._persistent_vault.restore_all(text)
