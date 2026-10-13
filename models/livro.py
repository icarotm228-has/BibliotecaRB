"""Models do acervo: Livro (obra) e Exemplar (unidade física com tombo)."""


class Livro:
    def __init__(self, titulo, autor, isbn, categoria, editora=None, id_livro=None):
        self.id_livro = id_livro
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.categoria = categoria
        self.editora = editora


class Exemplar:
    def __init__(self, tombo, id_livro, status="DISPONIVEL"):
        self.tombo = tombo
        self.id_livro = id_livro
        self.status = status

    @property
    def disponivel(self):
        return self.status == "DISPONIVEL"
