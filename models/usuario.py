"""Models de usuário: superclasse Usuario e subclasses por perfil."""


class Usuario:
    TIPO = None          # valor gravado em tb_usuario.tipo_usuario
    COTA_MAXIMA = None   # None = sem limite de livros simultâneos

    def __init__(self, nome, email, cpf, senha_hash="", status="ATIVO", id_usuario=None):
        self.id_usuario = id_usuario
        self.nome = nome
        self.email = email
        self.cpf = cpf
        self.senha_hash = senha_hash
        self.status = status

    @property
    def esta_ativo(self):
        return self.status == "ATIVO"

    def __repr__(self):
        return f"<{type(self).__name__} #{self.id_usuario} {self.nome} [{self.status}]>"


class Aluno(Usuario):
    TIPO = "ALUNO"
    COTA_MAXIMA = 3

    def __init__(self, nome, email, cpf, matricula, curso, **kw):
        super().__init__(nome, email, cpf, **kw)
        self.matricula = matricula
        self.curso = curso


class Professor(Usuario):
    TIPO = "PROFESSOR"

    def __init__(self, nome, email, cpf, siape, departamento, **kw):
        super().__init__(nome, email, cpf, **kw)
        self.siape = siape
        self.departamento = departamento


class Bibliotecario(Usuario):
    TIPO = "BIBLIOTECARIO"


class Administrador(Usuario):
    TIPO = "ADMIN"


def usuario_de_row(row):
    """Converte uma linha de tb_usuario na subclasse correta."""
    base = dict(senha_hash=row["senha_hash"], status=row["status"], id_usuario=row["id_usuario"])
    t = row["tipo_usuario"]
    if t == "ALUNO":
        return Aluno(row["nome"], row["email"], row["cpf"], row["matricula"], row["curso"], **base)
    if t == "PROFESSOR":
        return Professor(row["nome"], row["email"], row["cpf"], row["siape"], row["departamento"], **base)
    cls = Bibliotecario if t == "BIBLIOTECARIO" else Administrador
    return cls(row["nome"], row["email"], row["cpf"], **base)
