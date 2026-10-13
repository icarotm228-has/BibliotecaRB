"""DAO de usuários: só acesso a dados, sem regras de negócio."""
from models import usuario_de_row


class UsuarioDAO:
    def __init__(self, conn):
        self.conn = conn

    def inserir(self, u):
        cur = self.conn.execute(
            """INSERT INTO tb_usuario (nome, email, cpf, tipo_usuario, status, matricula, curso,
                                       siape, departamento, senha_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (u.nome, u.email, u.cpf, u.TIPO, u.status,
             getattr(u, "matricula", None), getattr(u, "curso", None),
             getattr(u, "siape", None), getattr(u, "departamento", None), u.senha_hash))
        u.id_usuario = cur.lastrowid
        return u.id_usuario

    def buscar_por_id(self, id_usuario):
        row = self.conn.execute("SELECT * FROM tb_usuario WHERE id_usuario=?", (id_usuario,)).fetchone()
        return usuario_de_row(row) if row else None

    def buscar_por_identificador(self, ident):
        """Login: aceita e-mail, matrícula ou SIAPE."""
        row = self.conn.execute(
            "SELECT * FROM tb_usuario WHERE email=? OR matricula=? OR siape=?", (ident, ident, ident)).fetchone()
        return usuario_de_row(row) if row else None

    def atualizar_status(self, id_usuario, status):
        self.conn.execute("UPDATE tb_usuario SET status=? WHERE id_usuario=?", (status, id_usuario))

    def contar(self):
        return self.conn.execute("SELECT COUNT(*) FROM tb_usuario").fetchone()[0]
