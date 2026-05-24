import pytest
from piupiu.privacy.vault import Vault, PLACEHOLDER_RE
from piupiu.privacy.regex_layer import RegexLayer
from piupiu.privacy.shield import PrivacyShield


def test_vault_store_and_restore():
    v = Vault()
    placeholder = v.store("AKIAIOSFODNN7EXAMPLE", "aws_key")
    assert PLACEHOLDER_RE.match(placeholder)
    assert "aws_key" in placeholder
    restored = v.restore_all(f"key is {placeholder} ok")
    assert "AKIAIOSFODNN7EXAMPLE" in restored


def test_vault_merge():
    v1, v2 = Vault(), Vault()
    p1 = v1.store("secret1", "password")
    p2 = v2.store("secret2", "token")
    v1.merge(v2)
    assert v1.restore_all(p2) == "secret2"


def test_vault_roundtrip_serialisation():
    v = Vault()
    v.store("original_value", "api_key")
    v2 = Vault.from_dict(v.to_dict())
    for uid, entry in v._store.items():
        assert v2._store[uid] == entry


@pytest.mark.asyncio
async def test_regex_connection_string():
    layer = RegexLayer()
    vault = Vault()
    text = "DB: postgresql://admin:s3cr3t@prod.db:5432/mydb"
    redacted = await layer.redact(text, vault)
    assert "s3cr3t" not in redacted
    assert "<SECRET:" in redacted


@pytest.mark.asyncio
async def test_regex_bearer_token():
    layer = RegexLayer()
    vault = Vault()
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"
    redacted = await layer.redact(text, vault)
    assert "eyJhbGciOiJIUzI1NiJ9" not in redacted


@pytest.mark.asyncio
async def test_regex_env_credential():
    layer = RegexLayer()
    vault = Vault()
    text = "API_KEY=sk-1234567890abcdef in your config"
    redacted = await layer.redact(text, vault)
    assert "sk-1234567890abcdef" not in redacted


@pytest.mark.asyncio
async def test_shield_redacts_and_builds_vault():
    shield = PrivacyShield(ollama=None)
    redacted, vault = await shield.redact("password=hunter2")
    assert "hunter2" not in redacted
    assert len(vault._store) > 0
