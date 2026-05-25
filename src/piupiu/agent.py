from __future__ import annotations
import logging

from .ai.base import AIProvider
from .channels.base import Message
from .config import Settings
from .graph.engine import GraphEngine
from .graph.schema import Edge, Node
from .graph.storage import GraphStorage
from .privacy.shield import PrivacyShield

logger = logging.getLogger(__name__)


class Agent:
    """Main orchestrator: privacy shield → AI → graph → reply."""

    def __init__(self, cfg: Settings) -> None:
        self._cfg = cfg
        self._shield = PrivacyShield.from_config(cfg)
        storage = GraphStorage(cfg.data_dir, cfg.passphrase)
        self._graph = GraphEngine(storage)
        self._ai = self._build_ai_provider(cfg)
        self._channel = self._build_channel()

    @staticmethod
    def _build_ai_provider(cfg: Settings):
        if cfg.ai_provider == "nim":
            from .ai.nim_provider import NIMProvider
            return NIMProvider(cfg.nim_api_key, cfg.nim_model, cfg.nim_base_url)
        from .ai.claude_provider import ClaudeProvider
        return ClaudeProvider(cfg.anthropic_api_key, cfg.ai_model)

    def _build_channel(self):
        if self._cfg.channel == "telegram":
            from .channels.telegram import TelegramChannel
            return TelegramChannel(self._cfg.telegram_bot_token, self.handle_message)
        from .channels.cli import CLIChannel
        return CLIChannel(self.handle_message)

    _GRAPH_COMMANDS = {"/graph", "/nodes", "/edges", "/dump"}

    _HELP_TEXT = """\
PiuPiu — private knowledge graph assistant

── Node types ───────────────────────────
  Organization   companies, teams, projects
  Person         people you know or work with
  Service        cloud services, apps, platforms
  Credential     logins, API keys, tokens
  Resource       files, URLs, servers, databases
  Concept        tags, topics, categories
  Event          meetings, deadlines, incidents
  Location       offices, regions, data centres

── Relationship types ───────────────────
  USES · OWNS · KNOWS · HAS_CREDENTIAL
  GRANTS_ACCESS_TO · BELONGS_TO
  RELATED_TO · WORKS_AT

── Adding nodes (just talk naturally) ───
  "Pristine's AWS root account is root@pristine.com, password is 'Tr0ub4dor&3'"
  "Alice Chen works at Pristine as lead DevOps engineer"
  "Pristine uses AWS, GitHub, and Cloudflare"
  "Alice owns the Cloudflare account"
  "The production Postgres is db.prod.example.com, port 5432, user=app, password='s3cr3t!'"

── Querying ─────────────────────────────
  "What are Pristine's credentials?"
  "What services does Pristine use?"
  "What is Alice's contact info?"
  "What is the production database password?"

── Commands ─────────────────────────────
  /graph   show all nodes and edges
  /help    show this message\
"""

    async def handle_message(self, msg: Message) -> None:
        try:
            logger.debug("── Incoming message from %s ────────────────────\n%s",
                         msg.sender_id, msg.text)

            cmd = msg.text.strip().lower()
            if cmd in self._GRAPH_COMMANDS:
                await self._channel.send(msg.chat_id, self._graph.dump())
                return

            if cmd == "/help":
                await self._channel.send(msg.chat_id, self._HELP_TEXT)
                return

            # 1. Redact sensitive data — nothing past this point contains originals
            redacted, vault = await self._shield.redact(msg.text)
            logger.debug("── After privacy shield ────────────────────────\n%s", redacted)
            if vault._store:
                logger.debug("── Vault entries (%d) ──────────────────────────\n%s",
                             len(vault._store),
                             "\n".join(f"  {uid}: [{t}]" for uid, (t, _) in vault._store.items()))

            # 2. Fetch relevant graph context for queries
            context = self._graph.get_context(redacted)
            if context:
                logger.debug("── Graph context (%d node(s)) ──────────────────\n%s",
                             len(context),
                             "\n".join(f"  [{n['type']}] {n['label']} props={n['properties']}"
                                       for n in context))

            # 3. Send redacted text + context to cloud AI
            result = await self._ai.process(redacted, context)
            logger.debug("── AI result  intent=%s  entities=%d  relations=%d ──\n%s",
                         result.intent, len(result.entities), len(result.relationships),
                         result.response)

            # 4. Persist extracted knowledge (originals restored from vault before storage)
            if result.intent in ("store", "query") and result.entities:
                for entity in result.entities:
                    self._graph.upsert_node(
                        Node(id=entity.id, type=entity.type,
                             label=entity.label, properties=entity.properties),
                        vault,
                    )
                for rel in result.relationships:
                    self._graph.upsert_edge(
                        Edge(from_id=rel.from_id, to_id=rel.to_id,
                             type=rel.type, properties=rel.properties),
                        vault,
                    )
                self._graph.persist()

            # 5. Build and send reply
            # Run through vault restoration as safety net in case the AI echoed a placeholder
            reply = self._graph.restore(result.response)
            if result.intent == "store" and result.entities:
                stats = self._graph.stats()
                reply += f"\n(Graph: {stats['nodes']} nodes, {stats['edges']} edges)"

            logger.debug("── Reply to user ────────────────────────────────\n%s", reply)
            await self._channel.send(msg.chat_id, reply)

        except Exception:
            logger.exception("Error handling message from %s", msg.sender_id)
            await self._channel.send(msg.chat_id, "Something went wrong — please try again.")

    async def run(self) -> None:
        logger.info("PiuPiu starting on channel: %s", self._cfg.channel)
        logger.info("Graph: %s", self._graph.stats())
        try:
            await self._channel.start()
        finally:
            self._graph.persist()
            logger.info("Graph persisted. Goodbye!")
