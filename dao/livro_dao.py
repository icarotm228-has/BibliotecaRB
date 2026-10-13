"""DAO do acervo (livros e exemplares)."""
from models import Exemplar


class LivroDAO:
    def __init__(self, conn):
        self.conn = conn

    def inserir_livro(self, l):
        cur = self.conn.execute(
            "INSERT INTO tb_livro (titulo, autor, isbn, categoria, editora) VALUES (?,?,?,?,?)",
            (l.titulo, l.autor, l.isbn, l.categoria, l.editora))
        l.id_livro = cur.lastrowid
        return l.id_livro

    def inserir_exemplar(self, e):
        self.conn.execute("INSERT INTO tb_exemplar (tombo, id_livro, status) VALUES (?,?,?)",
                          (e.tombo, e.id_livro, e.status))

    def buscar_exemplar(self, tombo):
        r = self.conn.execute("SELECT * FROM tb_exemplar WHERE tombo=?", (tombo,)).fetchone()
        return Exemplar(r["tombo"], r["id_livro"], r["status"]) if r else None

    def atualizar_status_exemplar(self, tombo, status):
        self.conn.execute("UPDATE tb_exemplar SET status=? WHERE tombo=?", (status, tombo))

    def buscar(self, termo=""):
        """Consulta ao acervo por título, autor ou categoria (RF-03)."""
        like = f"%{termo}%"
        return self.conn.execute(
            """SELECT l.titulo, l.autor, l.categoria, e.tombo, e.status
               FROM tb_livro l JOIN tb_exemplar e ON e.id_livro = l.id_livro
               WHERE l.titulo LIKE ? OR l.autor LIKE ? OR l.categoria LIKE ?
               ORDER BY l.titulo, e.tombo""", (like, like, like)).fetchall()
