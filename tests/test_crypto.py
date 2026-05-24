import pytest
from piupiu.crypto.keychain import derive_key
from piupiu.crypto.cipher import encrypt, decrypt


def test_key_derivation_is_deterministic():
    salt = b"testsalt" * 2  # 16 bytes
    key1, _ = derive_key("passphrase", salt)
    key2, _ = derive_key("passphrase", salt)
    assert key1 == key2
    assert len(key1) == 32


def test_different_passphrases_produce_different_keys():
    salt = b"testsalt" * 2
    key1, _ = derive_key("passphrase-a", salt)
    key2, _ = derive_key("passphrase-b", salt)
    assert key1 != key2


def test_encrypt_decrypt_roundtrip():
    key, _ = derive_key("test", b"salt" * 4)
    plaintext = b"super secret data 1234"
    assert decrypt(key, encrypt(key, plaintext)) == plaintext


def test_ciphertext_differs_from_plaintext():
    key, _ = derive_key("test", b"salt" * 4)
    plaintext = b"hello"
    assert encrypt(key, plaintext) != plaintext


def test_wrong_key_raises():
    key1, _ = derive_key("correct", b"salt" * 4)
    key2, _ = derive_key("wrong", b"salt" * 4)
    ciphertext = encrypt(key1, b"data")
    with pytest.raises(Exception):
        decrypt(key2, ciphertext)
