import os
from argon2.low_level import hash_secret_raw, Type

SALT_SIZE = 16
KEY_SIZE = 32


def derive_key(passphrase: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derive a 32-byte AES key from a passphrase using Argon2id."""
    if salt is None:
        salt = os.urandom(SALT_SIZE)
    key = hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=3,
        memory_cost=65536,  # 64 MB
        parallelism=4,
        hash_len=KEY_SIZE,
        type=Type.ID,
    )
    return key, salt
