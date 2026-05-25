from __future__ import annotations
import logging

import networkx as nx

from .schema import Edge, Node
from .storage import GraphStorage
from ..privacy.vault import Vault

logger = logging.getLogger(__name__)


class GraphEngine:
    """In-memory NetworkX graph backed by encrypted storage."""

    def __init__(self, storage: GraphStorage) -> None:
        self._storage = storage
        self._graph: nx.DiGraph = storage.load_graph()
        self._persistent_vault = Vault.from_dict(storage.load_vault_data())
        logger.info("Graph loaded: %s", self.stats())

    # ── write ─────────────────────────────────────────────────────────────

    def upsert_node(self, node: Node, session_vault: Vault) -> None:
        """Merge node into the graph, restoring any placeholders to originals."""
        label = self._restore(node.label, session_vault)
        props = {k: self._restore(str(v), session_vault) for k, v in node.properties.items()}
        self._graph.add_node(node.id, type=node.type, label=label, **props)
        self._persistent_vault.merge(session_vault)

    def upsert_edge(self, edge: Edge, session_vault: Vault) -> None:
        props = {k: self._restore(str(v), session_vault) for k, v in edge.properties.items()}
        self._graph.add_edge(edge.from_id, edge.to_id, type=edge.type, **props)

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

    def restore(self, text: str) -> str:
        """Replace any vault placeholders in text with their original values."""
        return self._persistent_vault.restore_all(text)

    def stats(self) -> dict:
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
        }

    # ── persistence ───────────────────────────────────────────────────────

    def persist(self) -> None:
        self._storage.save_graph(self._graph)
        self._storage.save_vault_data(self._persistent_vault.to_dict())
        logger.debug("Graph persisted: %s", self.stats())

    # ── helpers ───────────────────────────────────────────────────────────

    def _restore(self, text: str, session_vault: Vault) -> str:
        text = session_vault.restore_all(text)
        return self._persistent_vault.restore_all(text)
