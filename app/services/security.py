import hashlib
import hmac
import os

HASH_NAME = "sha256"
ITERATIONS = 210_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    password_hash = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_{HASH_NAME}${ITERATIONS}${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hash = password_hash.split("$", 3)
        _, hash_name = algorithm.split("_", 1)
    except ValueError:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        hash_name,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    ).hex()
    return hmac.compare_digest(actual_hash, expected_hash)
