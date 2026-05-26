from __future__ import annotations
import asyncio
import logging

from .ai.base import AIProvider
from .channels.base import Message
from .config import Settings
from .graph.engine import GraphEngine
from .graph.schema import Edge, Node
from .graph.storage import GraphStorage
from .privacy.shield import PrivacyShield
from .privacy.vault import Vault

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
  /graph           show all nodes and edges
  /show <name>     look up nodes by name (fuzzy match)
  /delete <name>   delete a node by name (fuzzy match)
  /help            show this message\
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

            if cmd.startswith("/show"):
                query = msg.text.strip()[5:].strip()
                if not query:
                    await self._channel.send(msg.chat_id, "Usage: /show <name>  e.g. /show pristine")
                    return
                await self._channel.send(msg.chat_id, self._graph.show_nodes(query))
                return

            if cmd.startswith("/delete"):
                query = msg.text.strip()[7:].strip()
                if not query:
                    await self._channel.send(msg.chat_id, "Usage: /delete <name>  e.g. /delete pristine")
                    return
                await self._channel.send(msg.chat_id, self._graph.delete_node(query))
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
                if result.intent == "store" and self._cfg.confirm_timeout > 0:
                    confirm_msg = self._format_confirmation(result, vault, context)
                    accepted = await self._channel.confirm(
                        msg.chat_id, confirm_msg, self._cfg.confirm_timeout
                    )
                    if not accepted:
                        logger.debug("── Storage rejected by user ─────────────────────")
                        await self._channel.send(msg.chat_id, "Nothing stored.")
                        return
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

    def _format_confirmation(self, result, vault: Vault, context: list[dict]) -> str:
        def restore(text: str) -> str:
            return self._graph.restore(vault.restore_all(str(text)))

        n_nodes = len(result.entities)
        n_edges = len(result.relationships)
        lines = [
            f"Store {n_nodes} node(s)"
            + (f" and {n_edges} edge(s)" if n_edges else "")
            + "?",
            "",
        ]
        for ent in result.entities:
            label = restore(ent.label)
            props = {k: restore(v) for k, v in (ent.properties or {}).items() if v}
            lines.append(f"[{ent.type}]  {label}")
            for k, v in props.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

        if result.relationships:
            id_to_label = {e.id: restore(e.label) for e in result.entities}
            lines.append("Edges:")
            for rel in result.relationships:
                fl = id_to_label.get(rel.from_id, rel.from_id)
                tl = id_to_label.get(rel.to_id, rel.to_id)
                lines.append(f"  {fl}  ──{rel.type}──►  {tl}")
            lines.append("")

        if context:
            lines.append("Related existing nodes:")
            for n in context:
                props = {k: v for k, v in (n.get("properties") or {}).items() if v}
                prop_str = (
                    f"  ({'; '.join(f'{k}: {v}' for k, v in props.items())})" if props else ""
                )
                lines.append(f"  [{n['type']}]  {n['label']}{prop_str}")

        return "\n".join(lines).rstrip()

    async def run(self) -> None:
        logger.info("PiuPiu starting on channel: %s", self._cfg.channel)
        logger.info("Graph: %s", self._graph.stats())
        coros = [self._channel.start()]
        if self._cfg.web_enabled:
            from .web.server import run_web
            logger.info("Web UI: http://%s:%d", self._cfg.web_host, self._cfg.web_port)
            coros.append(run_web(self._graph, self._cfg.web_host, self._cfg.web_port))
        try:
            await asyncio.gather(*coros)
        finally:
            self._graph.persist()
            logger.info("Graph persisted. Goodbye!")
