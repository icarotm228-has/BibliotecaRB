"""Hash de senha com PBKDF2 (biblioteca padrão, sem dependências externas)."""
import hashlib
import hmac
import os


def gerar_hash(senha: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 100_000)
    return f"{salt.hex()}${h.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    salt_hex, hash_hex = armazenado.split("$")
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), 100_000)
    return hmac.compare_digest(h.hex(), hash_hex)
