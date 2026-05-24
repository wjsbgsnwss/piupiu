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
