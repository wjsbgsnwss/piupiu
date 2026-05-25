import pytest
from piupiu.ai._context import format_context
from piupiu.privacy.regex_layer import RegexLayer
from piupiu.privacy.vault import Vault


# ── context formatter ────────────────────────────────────────────────────────

def test_properties_included_in_context():
    ctx = format_context([{
        "type": "Credential",
        "label": "Cloudflare Credential",
        "properties": {"username": "abc@gmail.com", "password": "s3cr3t"},
        "edges": [],
    }])
    assert "username: abc@gmail.com" in ctx
    assert "password: s3cr3t" in ctx


def test_edges_formatted_readably():
    ctx = format_context([{
        "type": "Service",
        "label": "Cloudflare",
        "properties": {},
        "edges": [{"to": "Pristine", "relation": "BELONGS_TO"}],
    }])
    assert "BELONGS_TO → Pristine" in ctx
    # must not contain raw Python dict repr
    assert "{'to'" not in ctx


def test_empty_context_returns_empty_string():
    assert format_context([]) == ""


def test_empty_properties_not_shown():
    ctx = format_context([{
        "type": "Service",
        "label": "GitHub",
        "properties": {},
        "edges": [],
    }])
    assert "(" not in ctx


# ── natural language credential redaction ────────────────────────────────────

@pytest.mark.asyncio
async def test_natural_language_password_is_redacted():
    layer = RegexLayer()
    vault = Vault()
    text = "the password is hunter2secure"
    redacted = await layer.redact(text, vault)
    assert "hunter2secure" not in redacted
    assert "<SECRET:" in redacted


@pytest.mark.asyncio
async def test_natural_language_password_with_quotes():
    layer = RegexLayer()
    vault = Vault()
    text = "my password is 'MyS3cr3tPass'"
    redacted = await layer.redact(text, vault)
    assert "MyS3cr3tPass" not in redacted


@pytest.mark.asyncio
async def test_env_assignment_still_works():
    layer = RegexLayer()
    vault = Vault()
    text = "TOKEN=abcdef1234567890"
    redacted = await layer.redact(text, vault)
    assert "abcdef1234567890" not in redacted
