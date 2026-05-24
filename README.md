# PiuPiu 🐦

> **P**rivate **I**nformation **U**nified, **P**owered by **I**ntelligent **U**nderstanding

A self-hosted AI assistant that **remembers everything you tell it** — credentials, contacts, notes, resources — and stores it all in an encrypted knowledge graph on your own machine. Chat with it over Telegram, Slack, or the CLI.

**Your secrets never leave your machine in plaintext. Ever.**

---

## Why PiuPiu?

Most AI assistants send everything you type to the cloud. PiuPiu doesn't.

Before any message reaches the AI, it passes through a **4-layer privacy shield** that detects and redacts passwords, API keys, tokens, and personal data — replacing them with anonymous placeholders. Only the sanitised text is sent to the cloud AI. The originals stay in an AES-256-GCM encrypted vault on your disk.

```
You: "My AWS key is AKIAIOSFODNN7EXAMPLE, use it for the prod bucket"

  ┌─────────────────────────────────┐
  │       Privacy Shield            │
  │  AKIAIOSFODNN7EXAMPLE  ──────►  <SECRET:aws_key:a3f9>   (stored locally)
  └────────────────────────────��────┘
                │
                ▼  (redacted text only)
          Claude API
                │
                ▼
  ┌──────────��──────────────────────┐
  │     Encrypted Graph DB          │
  │  Credential ──► prod bucket     │  (original restored before storage)
  └─────────��───────────────��───────┘
```

Later: *"What's my AWS key?"* → PiuPiu queries the local graph and tells you.

---

## Features

- **Privacy-first by design** — secrets redacted before any cloud call
- **4-layer shield** — Microsoft Presidio (PII) + Yelp detect-secrets (tokens) + regex patterns + optional local Ollama final check
- **Encrypted knowledge graph** — AES-256-GCM, key derived with Argon2id from your passphrase
- **Conversational memory** — ask natural questions, PiuPiu answers from your graph
- **Multi-channel** — Telegram bot, CLI (more coming)
- **Optional local AI** — run Ollama locally for a fully air-gapped privacy layer
- **Self-hosted** — no accounts, no subscriptions, no telemetry

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/YOUR_USERNAME/piupiu.git
cd piupiu
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
PIUPIU_PASSPHRASE=a-strong-passphrase-you-will-remember
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run (CLI mode)

```bash
python3 -m piupiu
```

```
PiuPiu CLI ready — type your message (Ctrl+C to exit)

> My GitHub token is ghp_abc123xyz and I use it for the wjsbgsnwss org
PiuPiu: Got it — I've linked your GitHub token to the wjsbgsnwss organisation.
        (Graph: 2 nodes, 1 edge)

> What token do I use for GitHub?
PiuPiu: Your GitHub token for wjsbgsnwss is ghp_abc123xyz.
```

---

## Telegram Setup

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy your token
2. Add to `.env`:

```env
PIUPIU_CHANNEL=telegram
TELEGRAM_BOT_TOKEN=your-token-here
```

3. Start PiuPiu and open your bot in Telegram.

---

## Privacy Shield Layers

| Layer | What it catches | Dependency |
|---|---|---|
| **Presidio** | Names, emails, phone numbers, IBANs, passports | `spacy` model (see below) |
| **detect-secrets** | AWS/GCP/Azure keys, Slack/Stripe tokens, JWTs, high-entropy strings | built-in |
| **Regex** | Connection strings, bearer tokens, `.env` credentials, private key blocks | built-in |
| **Ollama** | Contextual secrets pattern-matching misses (e.g. *"my password is my cat's name"*) | Ollama running locally |

### Enable Presidio PII detection

```bash
python3 -m spacy download en_core_web_sm
```

### Enable the Ollama final check

```bash
# Pull a small model
ollama pull qwen2.5:3b

# Enable in .env
PIUPIU_OLLAMA_ENABLED=true
PIUPIU_OLLAMA_BASE_URL=http://localhost:11434
PIUPIU_OLLAMA_MODEL=qwen2.5:3b
```

---

## How the Graph Works

Every message you send is decomposed into **entities** (people, credentials, services, resources) and **relationships** between them. These are stored as nodes and edges in an encrypted NetworkX graph.

```
[Person: Alice] ──WORKS_AT──► [Organization: Acme Corp]
[Person: Alice] ──HAS_CREDENTIAL──► [Credential: AWS key]
[Credential: AWS key] ──GRANTS_ACCESS_TO──► [Resource: prod-bucket]
```

When you ask a question, PiuPiu finds the relevant subgraph and gives it to the AI as context — so answers are grounded in *your* data, not hallucinated.

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `PIUPIU_PASSPHRASE` | *(required)* | Master key for graph encryption |
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic Claude API key |
| `PIUPIU_CHANNEL` | `cli` | `cli` or `telegram` |
| `PIUPIU_DATA_DIR` | `.piupiu` | Directory for encrypted data files |
| `PIUPIU_AI_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `TELEGRAM_BOT_TOKEN` | — | Required when channel is `telegram` |
| `PIUPIU_OLLAMA_ENABLED` | `false` | Enable Ollama privacy layer |
| `PIUPIU_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `PIUPIU_OLLAMA_MODEL` | `qwen2.5:3b` | Model for privacy checking |

---

## Architecture

```
Message (Telegram / CLI / …)
    │
    ▼
Privacy Shield ──── vault.enc (encrypted, local)
    │  redacted text only
    ▼
Claude API  (entity + relationship extraction)
    │  structured JSON
    ▼
Graph Engine ◄──── graph.enc (AES-256-GCM, local)
    │  restores originals from vault before writing
    ▼
Reply to user
```

Key files:

```
src/piupiu/
├── crypto/        Argon2id key derivation · AES-256-GCM cipher
├── privacy/       4-layer shield · encrypted vault
├── graph/         NetworkX engine · encrypted persistence
├── ai/            Claude provider · structured tool use
├── channels/      Telegram · CLI adapters
└── agent.py       Main orchestrator
```

---

## Running Tests

```bash
pip install -e ".[dev]"
python3 -m pytest tests/ -v
```

---

## Roadmap

- [ ] Slack channel adapter
- [ ] WhatsApp adapter (via Twilio / Meta Cloud API)
- [ ] Vector embeddings for semantic graph search
- [ ] Web UI for graph visualisation
- [ ] Multi-user support with per-user graph isolation
- [ ] Export / import graph

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

---

## License

MIT
