"""DAO de empréstimos."""
from models import Emprestimo
from models.emprestimo import dt_para_str, str_para_dt


def _de_row(r):
    return Emprestimo(r["id_usuario"], r["tombo_exemplar"], r["id_bibliotecario"],
                      str_para_dt(r["data_emprestimo"]), str_para_dt(r["data_prevista_devolucao"]),
                      str_para_dt(r["data_devolucao_real"]), r["status"], r["id_emprestimo"])


class EmprestimoDAO:
    def __init__(self, conn):
        self.conn = conn

    def inserir(self, e):
        cur = self.conn.execute(
            """INSERT INTO tb_emprestimo (id_usuario, tombo_exemplar, id_bibliotecario, data_emprestimo,
                                          data_prevista_devolucao, status) VALUES (?,?,?,?,?,?)""",
            (e.id_usuario, e.tombo_exemplar, e.id_bibliotecario, dt_para_str(e.data_emprestimo),
             dt_para_str(e.data_prevista_devolucao), e.status))
        e.id_emprestimo = cur.lastrowid
        return e.id_emprestimo

    def marcar_atrasados(self, agora):
        """Empréstimos ATIVOS com prazo vencido passam para ATRASADO."""
        self.conn.execute("UPDATE tb_emprestimo SET status='ATRASADO' "
                          "WHERE status='ATIVO' AND data_prevista_devolucao < ?", (dt_para_str(agora),))

    def listar_pendentes_do_usuario(self, id_usuario):
        rows = self.conn.execute("SELECT * FROM tb_emprestimo WHERE id_usuario=? "
                                 "AND status IN ('ATIVO','ATRASADO')", (id_usuario,)).fetchall()
        return [_de_row(r) for r in rows]

    def buscar_pendente_por_tombo(self, tombo):
        r = self.conn.execute("SELECT * FROM tb_emprestimo WHERE tombo_exemplar=? "
                              "AND status IN ('ATIVO','ATRASADO')", (tombo,)).fetchone()
        return _de_row(r) if r else None

    def concluir(self, id_emprestimo, data_real):
        self.conn.execute("UPDATE tb_emprestimo SET status='CONCLUIDO', data_devolucao_real=? "
                          "WHERE id_emprestimo=?", (dt_para_str(data_real), id_emprestimo))
