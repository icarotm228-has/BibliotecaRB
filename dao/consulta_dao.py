"""DAO de consultas com JOIN usadas pelas telas e relatórios (somente leitura)."""


class ConsultaDAO:
    def __init__(self, conn):
        self.conn = conn

    def listar_usuarios(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT id_usuario, nome, email, tipo_usuario, status, matricula, siape "
            "FROM tb_usuario ORDER BY tipo_usuario, nome")]

    def listar_emprestimos(self, pendentes=False, id_usuario=None):
        sql = """SELECT e.id_emprestimo, e.tombo_exemplar, l.titulo, u.nome AS usuario,
                        e.data_emprestimo, e.data_prevista_devolucao, e.data_devolucao_real, e.status
                 FROM tb_emprestimo e
                 JOIN tb_usuario u ON u.id_usuario = e.id_usuario
                 JOIN tb_exemplar x ON x.tombo = e.tombo_exemplar
                 JOIN tb_livro l ON l.id_livro = x.id_livro WHERE 1=1"""
        args = []
        if pendentes:
            sql += " AND e.status IN ('ATIVO','ATRASADO')"
        if id_usuario is not None:
            sql += " AND e.id_usuario = ?"
            args.append(id_usuario)
        sql += " ORDER BY e.data_prevista_devolucao"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def listar_advertencias(self, id_usuario=None):
        sql = """SELECT a.id_advertencia, u.nome AS usuario, a.motivo, a.dias_suspensao, e.tombo_exemplar
                 FROM tb_advertencia a
                 JOIN tb_usuario u ON u.id_usuario = a.id_usuario
                 LEFT JOIN tb_emprestimo e ON e.id_emprestimo = a.id_emprestimo"""
        args = []
        if id_usuario is not None:
            sql += " WHERE a.id_usuario = ?"
            args.append(id_usuario)
        return [dict(r) for r in self.conn.execute(sql + " ORDER BY a.id_advertencia DESC", args)]

    def metricas(self):
        q = lambda s: self.conn.execute(s).fetchone()[0]
        return {
            "livros": q("SELECT COUNT(*) FROM tb_livro"),
            "exemplares": q("SELECT COUNT(*) FROM tb_exemplar"),
            "ativos": q("SELECT COUNT(*) FROM tb_emprestimo WHERE status IN ('ATIVO','ATRASADO')"),
            "atrasados": q("SELECT COUNT(*) FROM tb_emprestimo WHERE status='ATRASADO'"),
            "suspensos": q("SELECT COUNT(*) FROM tb_usuario WHERE status='SUSPENSO'"),
        }
