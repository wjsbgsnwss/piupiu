import pytest
import tempfile
from pathlib import Path

from piupiu.graph.engine import GraphEngine
from piupiu.graph.schema import Edge, Node
from piupiu.graph.storage import GraphStorage
from piupiu.privacy.vault import Vault


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = GraphStorage(Path(tmpdir), "test-passphrase")
        yield GraphEngine(storage)


def test_upsert_and_query_node(engine):
    vault = Vault()
    engine.upsert_node(Node(id="n1", type="Person", label="Alice"), vault)
    context = engine.get_context("Alice")
    assert any(c["label"] == "Alice" for c in context)


def test_upsert_edge(engine):
    vault = Vault()
    engine.upsert_node(Node(id="n1", type="Person", label="Bob"), vault)
    engine.upsert_node(Node(id="n2", type="Service", label="GitHub"), vault)
    engine.upsert_edge(Edge(from_id="n1", to_id="n2", type="USES"), vault)
    assert engine.stats() == {"nodes": 2, "edges": 1}


def test_placeholder_restored_before_storage(engine):
    vault = Vault()
    placeholder = vault.store("AKIAIOSFODNN7EXAMPLE", "aws_key")
    engine.upsert_node(
        Node(id="cred1", type="Credential", label=placeholder), vault
    )
    context = engine.get_context("AKIAIOSFODNN7EXAMPLE")
    assert any(c["label"] == "AKIAIOSFODNN7EXAMPLE" for c in context)


def test_persist_and_reload(tmp_path):
    storage = GraphStorage(tmp_path, "pass")
    eng = GraphEngine(storage)
    vault = Vault()
    eng.upsert_node(Node(id="n1", type="Person", label="Carol"), vault)
    eng.persist()

    eng2 = GraphEngine(GraphStorage(tmp_path, "pass"))
    context = eng2.get_context("Carol")
    assert any(c["label"] == "Carol" for c in context)


def test_wrong_passphrase_on_reload(tmp_path):
    storage = GraphStorage(tmp_path, "correct")
    eng = GraphEngine(storage)
    eng.upsert_node(Node(id="n1", type="Person", label="Dave"), Vault())
    eng.persist()

    with pytest.raises(Exception):
        GraphEngine(GraphStorage(tmp_path, "wrong"))


def test_same_label_different_ai_ids_dedup(engine):
    """Two upserts with same type+label but different AI IDs → one canonical node."""
    vault = Vault()
    engine.upsert_node(Node(id="svc_1", type="Service", label="GitHub"), vault)
    engine.upsert_node(Node(id="svc_2", type="Service", label="GitHub"), vault)
    assert engine.stats()["nodes"] == 1


def test_edge_dedup(engine):
    """Same-type edge inserted twice → only one edge persisted."""
    vault = Vault()
    engine.upsert_node(Node(id="a1", type="Person", label="Eve"), vault)
    engine.upsert_node(Node(id="b1", type="Service", label="AWS"), vault)
    engine.upsert_edge(Edge(from_id="a1", to_id="b1", type="USES"), vault)
    engine.upsert_edge(Edge(from_id="a1", to_id="b1", type="USES"), vault)
    assert engine.stats() == {"nodes": 2, "edges": 1}


def test_canonical_id_used_for_edges(engine):
    """Edges reference AI IDs that are remapped to canonical node IDs."""
    vault = Vault()
    engine.upsert_node(Node(id="org_pristine", type="Organization", label="Pristine"), vault)
    engine.upsert_node(Node(id="cred_cloudflare", type="Credential", label="Cloudflare Login"), vault)
    engine.upsert_edge(Edge(from_id="cred_cloudflare", to_id="org_pristine", type="BELONGS_TO"), vault)
    assert engine.stats() == {"nodes": 2, "edges": 1}


def test_startup_dedup_on_reload(tmp_path):
    """Dirty graph with duplicate node IDs is deduped on next load."""
    import networkx as nx
    from piupiu.graph.storage import GraphStorage

    # Manually write a graph with two nodes that share type+label
    storage = GraphStorage(tmp_path, "pass")
    g = nx.DiGraph()
    g.add_node("cloudflare_1", type="Service", label="Cloudflare")
    g.add_node("cloudflare_2", type="Service", label="Cloudflare")
    g.add_edge("cloudflare_1", "cloudflare_2", type="RELATED_TO")
    storage.save_graph(g)
    storage.save_vault_data({})

    eng = GraphEngine(storage)
    assert eng.stats()["nodes"] == 1
    assert eng.stats()["edges"] == 0  # self-loop removed after merge
