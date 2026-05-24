from __future__ import annotations
import json
import logging
from pathlib import Path

import networkx as nx

from ..crypto.cipher import decrypt, encrypt
from ..crypto.keychain import derive_key

logger = logging.getLogger(__name__)

_SALT_FILE = "salt.bin"
_GRAPH_FILE = "graph.enc"
_VAULT_FILE = "vault.enc"


class GraphStorage:
    """Encrypted persistence for the knowledge graph and the secret vault."""

    def __init__(self, data_dir: Path, passphrase: str) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_create_key(passphrase)

    def _load_or_create_key(self, passphrase: str) -> bytes:
        salt_path = self._dir / _SALT_FILE
        if salt_path.exists():
            key, _ = derive_key(passphrase, salt_path.read_bytes())
        else:
            key, salt = derive_key(passphrase)
            salt_path.write_bytes(salt)
            logger.info("New encryption salt created at %s", salt_path)
        return key

    def save_graph(self, graph: nx.DiGraph) -> None:
        data = nx.node_link_data(graph)
        plaintext = json.dumps(data, default=str).encode()
        (self._dir / _GRAPH_FILE).write_bytes(encrypt(self._key, plaintext))

    def load_graph(self) -> nx.DiGraph:
        path = self._dir / _GRAPH_FILE
        if not path.exists():
            return nx.DiGraph()
        plaintext = decrypt(self._key, path.read_bytes())
        return nx.node_link_graph(json.loads(plaintext))

    def save_vault_data(self, data: dict) -> None:
        plaintext = json.dumps(data).encode()
        (self._dir / _VAULT_FILE).write_bytes(encrypt(self._key, plaintext))

    def load_vault_data(self) -> dict:
        path = self._dir / _VAULT_FILE
        if not path.exists():
            return {}
        plaintext = decrypt(self._key, path.read_bytes())
        return json.loads(plaintext)
