"""Camada Database: conexão SQLite, transações e criação do schema."""
import os
import sqlite3
from contextlib import contextmanager

DB_DIR = os.path.dirname(os.path.abspath(__file__))   # pasta database/
DB_PATH = os.environ.get("BIBLIOTECARB_DB", os.path.join(DB_DIR, "bibliotecarb.db"))
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row            # acesso às colunas por nome
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite não liga FKs por padrão
    return conn


@contextmanager
def transacao():
    """Abre uma conexão; faz commit ao final ou rollback se houver erro."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Cria as tabelas (se ainda não existirem) a partir do schema.sql."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        script = f.read()
    with transacao() as conn:
        conn.executescript(script)
