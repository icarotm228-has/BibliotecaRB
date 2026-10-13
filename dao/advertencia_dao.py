"""DAO de advertências."""
from models import Advertencia


class AdvertenciaDAO:
    def __init__(self, conn):
        self.conn = conn

    def inserir(self, a):
        cur = self.conn.execute(
            "INSERT INTO tb_advertencia (id_usuario, id_emprestimo, motivo, dias_suspensao) VALUES (?,?,?,?)",
            (a.id_usuario, a.id_emprestimo, a.motivo, a.dias_suspensao))
        a.id_advertencia = cur.lastrowid
        return a.id_advertencia

    def listar_por_usuario(self, id_usuario):
        rows = self.conn.execute("SELECT * FROM tb_advertencia WHERE id_usuario=?", (id_usuario,)).fetchall()
        return [Advertencia(r["id_usuario"], r["id_emprestimo"], r["motivo"], r["dias_suspensao"],
                            r["id_advertencia"]) for r in rows]
