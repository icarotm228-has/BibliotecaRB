"""
BibliotecaRB - MVP (Flask + Flask-SQLAlchemy + SQLite).

Como executar:
    python -m venv venv && source venv/bin/activate      # Windows: venv/Scripts/activate
    pip install -r requirements.txt
    python app.py                                        # abre em http://127.0.0.1:5000

Opções (todas opcionais):
    python app.py --db caminho/do/banco.db   usa um banco SQLite já existente
    python app.py --demo                     liga o MODO DEMONSTRAÇÃO (padrão: DESLIGADO)
    python app.py --reset                    apaga o banco e recria com os dados iniciais de teste

Persistência: SQLAlchemy (ORM). As tabelas são criadas por db.create_all() em database/bibliotecarb.db
(o arquivo database/schema.sql fica apenas como referência do esquema). Bancos já existentes são
mantidos e reaproveitados. Se o banco estiver vazio, é populado com dados de teste:
    admin@rb.edu / admin123  |  bib@rb.edu / bib123
    2026001 (aluno ativo) / 123456  |  2026002 (aluno suspenso) / 123456
O modo demonstração (troca de perfil sem senha e botão "Simular atraso") também liga com DEMO_MODE=1
ou editando MODO_DEMO abaixo.
"""
import argparse
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup, escape
from sqlalchemy import event, inspect as sa_inspect, or_, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash


def _ler_argumentos():
    ap = argparse.ArgumentParser(description="BibliotecaRB - MVP (Flask + SQLAlchemy)")
    ap.add_argument("--db", help="caminho de um banco SQLite existente (padrão: database/bibliotecarb.db)")
    ap.add_argument("--demo", action="store_true", help="liga o modo demonstração")
    ap.add_argument("--reset", action="store_true", help="apaga o banco e recria com os dados de teste")
    return ap.parse_args()


ARGS = _ler_argumentos() if __name__ == "__main__" else None   # lido antes de criar o engine do banco

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BIBLIOTECARB_DB", os.path.join(BASE_DIR, "database", "bibliotecarb.db"))
if ARGS and ARGS.db:
    DB_PATH = os.path.abspath(ARGS.db)

# MODO DEMONSTRAÇÃO: atalhos de troca de perfil sem senha e botão "Simular atraso". Padrão DESLIGADO.
MODO_DEMO = False
if os.environ.get("DEMO_MODE", "").strip() in ("0", "1"):
    MODO_DEMO = os.environ["DEMO_MODE"].strip() == "1"
if ARGS and ARGS.demo:
    MODO_DEMO = True

FMT = "%Y-%m-%d %H:%M:%S"
PRAZO_DIAS = {"ALUNO": 14, "PROFESSOR": 30}   # RN-01
COTA = {"ALUNO": 3}                           # cota de livros simultâneos (sem limite para professor)
LEITORES = ("ALUNO", "PROFESSOR")
ABERTOS = ("ATIVO", "ATRASADO")               # status de empréstimos ainda não devolvidos

app = Flask(__name__)
app.config.update(
    # Em produção defina a variável de ambiente SECRET_KEY; o padrão serve só para desenvolvimento.
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-esta-chave"),
    MODO_DEMO=MODO_DEMO,
    SQLALCHEMY_DATABASE_URI="sqlite:///" + Path(DB_PATH).as_posix(),   # sqlite:////caminho/absoluto/banco.db
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy()
db.init_app(app)


@event.listens_for(Engine, "connect")
def ativar_chaves_estrangeiras(conexao, _registro):
    """SQLite não aplica FOREIGN KEY por padrão; liga a verificação em cada conexão."""
    if isinstance(conexao, sqlite3.Connection):
        cur = conexao.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.close()


def agora():
    """Data/hora local sem microssegundos (mesmo relógio usado nas comparações de prazo).
    Usado no lugar de datetime.utcnow (obsoleto no Python 3.12 e em outro fuso)."""
    return datetime.now().replace(microsecond=0)


# ----------------------------------------------------------------------------
# Modelos (ORM) - tabelas tb_* da documentação
# ----------------------------------------------------------------------------
class Usuario(db.Model):
    __tablename__ = "tb_usuario"
    __table_args__ = (
        db.CheckConstraint("tipo_usuario IN ('ALUNO','PROFESSOR','BIBLIOTECARIO','ADMIN')", name="ck_usuario_tipo"),
        db.CheckConstraint("status IN ('ATIVO','SUSPENSO','INATIVO')", name="ck_usuario_status"),
    )
    id_usuario = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(20), nullable=False, unique=True)
    tipo_usuario = db.Column(db.String(20), nullable=False)      # ALUNO, PROFESSOR, BIBLIOTECARIO, ADMIN
    status = db.Column(db.String(15), nullable=False, default="ATIVO")
    matricula = db.Column(db.String(30), unique=True)            # alunos
    curso = db.Column(db.String(80))
    siape = db.Column(db.String(30), unique=True)                # professores
    departamento = db.Column(db.String(80))
    senha_hash = db.Column(db.String(255), nullable=False)

    # 1..N com Emprestimo (como cliente) e com Advertencia
    emprestimos = db.relationship("Emprestimo", back_populates="cliente", foreign_keys="Emprestimo.id_usuario")
    advertencias = db.relationship("Advertencia", back_populates="usuario")

    @property
    def esta_ativo(self):
        return self.status == "ATIVO"

    @property
    def cota_maxima(self):
        return COTA.get(self.tipo_usuario)


class Livro(db.Model):
    __tablename__ = "tb_livro"
    id_livro = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    editora = db.Column(db.String(120))

    exemplares = db.relationship("Exemplar", back_populates="livro", order_by="Exemplar.tombo")


class Exemplar(db.Model):
    __tablename__ = "tb_exemplar"
    __table_args__ = (db.CheckConstraint("status IN ('DISPONIVEL','EMPRESTADO','DANIFICADO')", name="ck_exemplar_status"),)
    tombo = db.Column(db.String(30), primary_key=True)            # código patrimonial único
    id_livro = db.Column(db.Integer, db.ForeignKey("tb_livro.id_livro"), nullable=False)
    status = db.Column(db.String(15), nullable=False, default="DISPONIVEL")

    livro = db.relationship("Livro", back_populates="exemplares")
    emprestimos = db.relationship("Emprestimo", back_populates="exemplar")


class Emprestimo(db.Model):
    __tablename__ = "tb_emprestimo"
    __table_args__ = (db.CheckConstraint("status IN ('ATIVO','CONCLUIDO','ATRASADO')", name="ck_emprestimo_status"),)
    id_emprestimo = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("tb_usuario.id_usuario"), nullable=False)
    tombo_exemplar = db.Column(db.String(30), db.ForeignKey("tb_exemplar.tombo"), nullable=False)
    id_bibliotecario = db.Column(db.Integer, db.ForeignKey("tb_usuario.id_usuario"), nullable=False)
    data_emprestimo = db.Column(db.DateTime, nullable=False, default=agora)
    data_prevista_devolucao = db.Column(db.DateTime, nullable=False)
    data_devolucao_real = db.Column(db.DateTime)
    status = db.Column(db.String(15), nullable=False, default="ATIVO")

    # dois vínculos com Usuario: o cliente (quem pegou) e o bibliotecário (quem registrou)
    cliente = db.relationship("Usuario", foreign_keys=[id_usuario], back_populates="emprestimos")
    bibliotecario = db.relationship("Usuario", foreign_keys=[id_bibliotecario])
    exemplar = db.relationship("Exemplar", back_populates="emprestimos")
    advertencias = db.relationship("Advertencia", back_populates="emprestimo")

    @property
    def titulo(self):
        return self.exemplar.livro.titulo

    def dias_de_atraso(self, referencia=None):
        """0 se no prazo; senão a quantidade de dias de atraso (mínimo 1)."""
        referencia = referencia or agora()
        if referencia <= self.data_prevista_devolucao:
            return 0
        return max(1, (referencia - self.data_prevista_devolucao).days)

    @property
    def dias_atraso(self):
        return 0 if self.data_devolucao_real else self.dias_de_atraso()


class Advertencia(db.Model):
    __tablename__ = "tb_advertencia"
    id_advertencia = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("tb_usuario.id_usuario"), nullable=False)
    id_emprestimo = db.Column(db.Integer, db.ForeignKey("tb_emprestimo.id_emprestimo"), nullable=True)
    motivo = db.Column(db.String(255), nullable=False)
    dias_suspensao = db.Column(db.Integer)
    data_ocorrencia = db.Column(db.DateTime, default=agora)

    usuario = db.relationship("Usuario", back_populates="advertencias")
    emprestimo = db.relationship("Emprestimo", back_populates="advertencias")


# ----------------------------------------------------------------------------
# Inicialização do banco e seeder
# ----------------------------------------------------------------------------
def init_db():
    """Cria as tabelas (db.create_all), ajusta bancos antigos e popula dados de teste se estiver vazio."""
    with app.app_context():
        novo = not os.path.exists(DB_PATH)
        print(f"[BibliotecaRB] Banco SQLite (SQLAlchemy): {DB_PATH} ({'criando' if novo else 'usando banco existente'})", flush=True)
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        db.create_all()                      # só cria o que ainda não existe
        colunas = [c["name"] for c in sa_inspect(db.engine).get_columns("tb_advertencia")]
        if "data_ocorrencia" not in colunas:  # banco criado por versão anterior
            db.session.execute(text("ALTER TABLE tb_advertencia ADD COLUMN data_ocorrencia DATETIME"))
            db.session.commit()
            print("[BibliotecaRB] Banco antigo atualizado: coluna data_ocorrencia adicionada", flush=True)
        if Usuario.query.count() == 0:
            seed()
            print("[BibliotecaRB] Banco vazio: dados iniciais de teste inseridos", flush=True)
        print(f"[BibliotecaRB] Dados no banco: {Usuario.query.count()} usuários, {Livro.query.count()} livros, "
              f"{Exemplar.query.count()} exemplares, {Emprestimo.query.count()} empréstimos, "
              f"{Advertencia.query.count()} advertências", flush=True)


def seed():
    """Dados fictícios de teste (executado apenas com o banco vazio)."""
    def usuario(nome, email, cpf, tipo, senha, **extra):
        return Usuario(nome=nome, email=email, cpf=cpf, tipo_usuario=tipo, senha_hash=generate_password_hash(senha), **extra)

    db.session.add_all([
        usuario("Admin Teste", "admin@rb.edu", "000.000.000-00", "ADMIN", "admin123"),
        usuario("Bibliotecário Teste", "bib@rb.edu", "111.111.111-11", "BIBLIOTECARIO", "bib123"),
        usuario("Aluno Exemplo", "aluno@rb.edu", "222.222.222-22", "ALUNO", "123456", matricula="2026001", curso="Informática"),
        usuario("Aluno Pendente", "pendente@rb.edu", "333.333.333-33", "ALUNO", "123456", matricula="2026002",
                curso="Informática", status="SUSPENSO"),
    ])
    dom = Livro(titulo="Dom Casmurro", autor="Machado de Assis", isbn="9788535910663", categoria="Romance",
                editora="Companhia das Letras")
    fis = Livro(titulo="Introdução à Física", autor="H. Moysés Nussenzveig", isbn="9788521207450",
                categoria="Ciências", editora="Blucher")
    db.session.add_all([dom, fis])
    db.session.flush()                       # gera id_livro para vincular os exemplares
    db.session.add_all([Exemplar(tombo="TOMB-001", id_livro=dom.id_livro), Exemplar(tombo="TOMB-002", id_livro=dom.id_livro),
                        Exemplar(tombo="TOMB-003", id_livro=fis.id_livro)])
    db.session.commit()


def atualizar_atrasados():
    """Empréstimos ATIVOS com prazo vencido passam para ATRASADO."""
    Emprestimo.query.filter(Emprestimo.status == "ATIVO", Emprestimo.data_prevista_devolucao < agora()) \
        .update({"status": "ATRASADO"}, synchronize_session=False)
    db.session.commit()


def buscar_usuario(identificador):
    """Localiza por e-mail, matrícula ou SIAPE."""
    if not identificador:
        return None
    return Usuario.query.filter(or_(Usuario.email == identificador, Usuario.matricula == identificador,
                                    Usuario.siape == identificador)).first()


# ----------------------------------------------------------------------------
# Segurança: login, perfis e CSRF
# ----------------------------------------------------------------------------
def roles_required(*tipos):
    """Exige login e que o perfil (ADMIN, BIBLIOTECARIO, ALUNO, PROFESSOR) esteja em `tipos`."""
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            u = db.session.get(Usuario, session["user_id"]) if "user_id" in session else None
            if u is None:                    # sem sessão, ou usuário não existe mais (ex.: banco recriado)
                session.clear()
                return redirect(url_for("login"))
            g.usuario = u
            if tipos and session["tipo"] not in tipos:
                flash("Você não tem permissão para acessar esta área.", "error")
                return redirect(url_for("index"))
            return f(*a, **kw)
        return wrapper
    return deco


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def verificar_csrf():
    if request.method == "POST":
        esperado = session.get("_csrf")
        if not esperado or not secrets.compare_digest(request.form.get("csrf_token", ""), esperado):
            abort(400, "Token CSRF inválido. Recarregue a página e tente novamente.")


def verificar_senha(senha_hash, senha):
    """Aceita o hash do Werkzeug e também o formato 'salt$hash' (PBKDF2) usado pelo backend anterior."""
    if senha_hash.count("$") == 1 and ":" not in senha_hash:
        salt_hex, hash_hex = senha_hash.split("$")
        try:
            h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), 100_000)
        except ValueError:
            return False
        return hmac.compare_digest(h.hex(), hash_hex)
    return check_password_hash(senha_hash, senha)


# ----------------------------------------------------------------------------
# Helpers de template (badges, datas, modo demo)
# ----------------------------------------------------------------------------
BADGES = {"DISPONIVEL": ("Disponível", "green"), "ATIVO": ("Ativo", "green"), "CONCLUIDO": ("Concluído", "green"),
          "EMPRESTADO": ("Emprestado", "yellow"), "SUSPENSO": ("Suspenso", "red"), "ATRASADO": ("Atrasado", "red"),
          "DANIFICADO": ("Danificado", "red"), "INATIVO": ("Inativo", "gray")}
CORES = {"green": "bg-green-100 text-green-800", "yellow": "bg-yellow-100 text-yellow-800",
         "red": "bg-red-100 text-red-800", "gray": "bg-slate-100 text-slate-600"}
PERFIS = {"ADMIN": "Administrador", "BIBLIOTECARIO": "Bibliotecário", "ALUNO": "Aluno", "PROFESSOR": "Professor"}


@app.template_global()
def badge(status):
    label, cor = BADGES.get(status, (status, "gray"))
    return Markup(f'<span class="px-2 py-0.5 rounded-full text-xs font-semibold {CORES[cor]}">{escape(label)}</span>')


@app.template_filter("data")
def fmt_data(valor, com_hora=False):
    if not valor:
        return "—"
    if isinstance(valor, str):
        valor = datetime.strptime(valor, FMT)
    return valor.strftime("%d/%m/%Y %H:%M" if com_hora else "%d/%m/%Y")


app.jinja_env.globals["PERFIS"] = PERFIS


@app.context_processor
def injetar_modo_demo():
    return {"MODO_DEMO": app.config["MODO_DEMO"]}   # lido a cada requisição pelos templates


# ----------------------------------------------------------------------------
# Autenticação (UC-01)
# ----------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = buscar_usuario(request.form.get("identificador", "").strip())
        senha = request.form.get("senha", "")
        if not u or not verificar_senha(u.senha_hash, senha):
            flash("Credenciais inválidas. Tente novamente.", "error")
        elif u.status == "INATIVO":
            flash("Acesso desativado. Procure a administração da biblioteca.", "error")
        else:
            session.clear()
            session.update(user_id=u.id_usuario, nome=u.nome, tipo=u.tipo_usuario)
            if u.status == "SUSPENSO":
                flash("Seu cadastro está suspenso: novos empréstimos estão bloqueados.", "warning")
            return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/entrar-como/<tipo>", methods=["POST"])
def entrar_como(tipo):
    """MODO DEMO: entra direto com a primeira conta do perfil (alternador de perfil)."""
    if not app.config["MODO_DEMO"] or tipo not in PERFIS:
        abort(404)
    u = Usuario.query.filter_by(tipo_usuario=tipo) \
        .order_by((Usuario.status == "ATIVO").desc(), Usuario.id_usuario).first()   # aluno: prefere conta ativa
    if not u:
        abort(404)
    session.clear()
    session.update(user_id=u.id_usuario, nome=u.nome, tipo=u.tipo_usuario)
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ----------------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------------
@app.route("/")
@app.route("/dashboard")
@roles_required()
def index():
    atualizar_atrasados()
    if session["tipo"] in ("ADMIN", "BIBLIOTECARIO"):
        m = {"staff": True,
             "livros": Livro.query.count(),
             "exemplares": Exemplar.query.count(),
             "ativos": Emprestimo.query.filter(Emprestimo.status.in_(ABERTOS)).count(),
             "atrasados": Emprestimo.query.filter_by(status="ATRASADO").count(),
             "suspensos": Usuario.query.filter_by(status="SUSPENSO").count()}
    else:
        uid = g.usuario.id_usuario
        m = {"staff": False,
             "ativos": Emprestimo.query.filter(Emprestimo.id_usuario == uid, Emprestimo.status.in_(ABERTOS)).count(),
             "atrasados": Emprestimo.query.filter_by(id_usuario=uid, status="ATRASADO").count(),
             "advertencias": Advertencia.query.filter_by(id_usuario=uid).count(),
             "status": g.usuario.status}
    return render_template("index.html", m=m)


# ----------------------------------------------------------------------------
# Acervo (UC-02 consulta, UC-08 cadastro)
# ----------------------------------------------------------------------------
@app.route("/acervo", methods=["GET", "POST"])
@roles_required("BIBLIOTECARIO", "ALUNO", "PROFESSOR")
def acervo():
    if request.method == "POST":
        if session["tipo"] != "BIBLIOTECARIO":
            abort(403)
        f = {k: request.form.get(k, "").strip() for k in ("titulo", "autor", "isbn", "categoria", "editora")}
        tombos = list(dict.fromkeys(t for t in re.split(r"[,;\s]+", request.form.get("tombos", "")) if t))
        if not (f["titulo"] and f["autor"] and f["isbn"] and f["categoria"]) or not tombos:
            flash("Preencha título, autor, ISBN, categoria e ao menos um tombo.", "error")
        elif Exemplar.query.filter(Exemplar.tombo.in_(tombos)).first():
            flash("Tombo já cadastrado. Cada exemplar precisa de um tombo único.", "error")
        else:
            try:
                livro = Livro(titulo=f["titulo"], autor=f["autor"], isbn=f["isbn"], categoria=f["categoria"],
                              editora=f["editora"] or None)
                db.session.add(livro)
                db.session.flush()           # gera id_livro
                db.session.add_all([Exemplar(tombo=t, id_livro=livro.id_livro) for t in tombos])
                db.session.commit()
                flash(f"Livro cadastrado com {len(tombos)} exemplar(es).", "success")
            except IntegrityError:
                db.session.rollback()
                flash("Não foi possível cadastrar: tombo duplicado ou dados inválidos.", "error")
        return redirect(url_for("acervo"))

    q = request.args.get("q", "").strip()
    consulta = Livro.query
    if q:
        like = f"%{q}%"
        consulta = consulta.filter(or_(Livro.titulo.ilike(like), Livro.autor.ilike(like), Livro.categoria.ilike(like)))
    # a busca em tempo real (enquanto digita) é feita no navegador; Enter aplica o filtro no servidor
    return render_template("acervo.html", livros=consulta.order_by(Livro.titulo).all(), q=q)


# ----------------------------------------------------------------------------
# Usuários (UC-05, UC-06, UC-07) - somente Administrador
# ----------------------------------------------------------------------------
@app.route("/usuarios", methods=["GET", "POST"])
@roles_required("ADMIN")
def usuarios():
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "cadastrar":
            val = lambda k: request.form.get(k, "").strip()
            tipo = val("tipo")
            erro = None
            if tipo not in ("ALUNO", "PROFESSOR", "BIBLIOTECARIO"):
                erro = "Tipo de usuário inválido."
            elif not (val("nome") and val("email") and val("cpf") and val("senha")):
                erro = "Preencha nome, e-mail, CPF e senha."
            elif tipo == "ALUNO" and not val("matricula"):
                erro = "Informe a matrícula do aluno."
            elif tipo == "PROFESSOR" and not val("siape"):
                erro = "Informe o SIAPE do professor."
            if erro:
                flash(erro, "error")
            else:
                aluno, prof = tipo == "ALUNO", tipo == "PROFESSOR"
                novo = Usuario(nome=val("nome"), email=val("email"), cpf=val("cpf"), tipo_usuario=tipo, status="ATIVO",
                               matricula=(val("matricula") or None) if aluno else None,
                               curso=(val("curso") or None) if aluno else None,
                               siape=(val("siape") or None) if prof else None,
                               departamento=(val("departamento") or None) if prof else None,
                               senha_hash=generate_password_hash(val("senha")))
                try:
                    db.session.add(novo)
                    db.session.commit()
                    flash("Usuário cadastrado com sucesso!", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("CPF, matrícula ou SIAPE já cadastrado no sistema.", "error")
        elif acao == "status":
            novo_status = request.form.get("novo_status")
            id_alvo = request.form.get("id_usuario", type=int)
            alvo = db.session.get(Usuario, id_alvo) if id_alvo is not None else None
            if novo_status not in ("ATIVO", "SUSPENSO") or not alvo or alvo.tipo_usuario == "ADMIN":
                flash("Operação inválida.", "error")
            else:
                alvo.status = novo_status
                db.session.commit()
                flash(f"Cadastro de {alvo.nome} {'suspenso' if novo_status == 'SUSPENSO' else 'reativado'}.", "success")
        return redirect(url_for("usuarios"))

    return render_template("usuarios.html", lista=Usuario.query.order_by(Usuario.tipo_usuario, Usuario.nome).all())


# ----------------------------------------------------------------------------
# Empréstimo no balcão (UC-09, UC-11) - Bibliotecário
# ----------------------------------------------------------------------------
@app.route("/emprestimo", methods=["GET", "POST"])
@roles_required("BIBLIOTECARIO")
def emprestimos():
    if request.method == "POST":
        ident = request.form.get("identificador", "").strip()
        tombo = request.form.get("tombo", "").strip()
        atualizar_atrasados()
        u = buscar_usuario(ident)
        ex = db.session.get(Exemplar, tombo) if tombo else None
        erro = None
        if not u:
            erro = "Usuário não encontrado."
        elif u.tipo_usuario not in LEITORES:
            erro = "Apenas alunos e professores podem pegar livros emprestados."
        elif u.status != "ATIVO":
            erro = f"Empréstimo não permitido: cadastro {u.status.lower()}."
        else:
            abertos = [e for e in u.emprestimos if e.status in ABERTOS]
            if any(e.status == "ATRASADO" for e in abertos):
                erro = "Empréstimo não permitido: usuário possui itens em atraso."
            elif u.cota_maxima is not None and len(abertos) >= u.cota_maxima:
                erro = f"Cota máxima atingida: {u.cota_maxima} livros simultâneos."
            elif not ex:
                erro = "Exemplar não encontrado."
            elif ex.status != "DISPONIVEL":
                erro = f"Empréstimo não permitido: exemplar {ex.status.lower()}."
        if erro:
            flash(erro, "error")
        else:
            inicio = agora()
            prevista = inicio + timedelta(days=PRAZO_DIAS[u.tipo_usuario])
            db.session.add(Emprestimo(id_usuario=u.id_usuario, tombo_exemplar=ex.tombo, id_bibliotecario=g.usuario.id_usuario,
                                      data_emprestimo=inicio, data_prevista_devolucao=prevista, status="ATIVO"))
            ex.status = "EMPRESTADO"
            db.session.commit()              # grava empréstimo e status do exemplar na mesma transação
            flash(f"Empréstimo registrado para {u.nome}. Devolução até {prevista.strftime('%d/%m/%Y')}.", "success")
        return redirect(url_for("emprestimos"))

    recentes = Emprestimo.query.order_by(Emprestimo.id_emprestimo.desc()).limit(8).all()
    return render_template("emprestimo.html", recentes=recentes, cota=COTA["ALUNO"])


# ----------------------------------------------------------------------------
# Devolução e punições (UC-10, UC-12) - Bibliotecário
# ----------------------------------------------------------------------------
@app.route("/devolucao", methods=["GET", "POST"])
@roles_required("BIBLIOTECARIO")
def devolucoes():
    if request.method == "POST":
        tombo = request.form.get("tombo", "").strip()
        danificado = request.form.get("danificado") == "on"
        emp = Emprestimo.query.filter(Emprestimo.tombo_exemplar == tombo, Emprestimo.status.in_(ABERTOS)).first()
        if not emp:
            flash("Nenhum empréstimo ativo para este tombo.", "error")
            return redirect(url_for("devolucoes"))
        devolvido_em = agora()
        atraso = emp.dias_de_atraso(devolvido_em)       # > 0 quando devolvido_em > data prevista
        emp.data_devolucao_real = devolvido_em
        emp.status = "CONCLUIDO"
        emp.exemplar.status = "DANIFICADO" if danificado else "DISPONIVEL"
        if atraso:
            db.session.add(Advertencia(id_usuario=emp.id_usuario, id_emprestimo=emp.id_emprestimo,
                                       motivo=f"Devolução do exemplar {tombo} com {atraso} dia(s) de atraso",
                                       dias_suspensao=atraso, data_ocorrencia=devolvido_em))
            emp.cliente.status = "SUSPENSO"
        db.session.commit()                  # devolução + advertência + suspensão numa única transação
        flash(f"Devolução do tombo {tombo} registrada.", "success")
        if atraso:
            flash(f"Infração: {atraso} dia(s) de atraso. Advertência registrada e usuário suspenso.", "warning")
        if danificado:
            flash("Exemplar marcado como danificado.", "warning")
        return redirect(url_for("devolucoes"))

    atualizar_atrasados()
    abertos = Emprestimo.query.filter(Emprestimo.status.in_(ABERTOS)).order_by(Emprestimo.data_prevista_devolucao).all()
    return render_template("devolucao.html", abertos=abertos)


@app.route("/emprestimo/<int:id_emp>/simular-atraso", methods=["POST"])
@roles_required("BIBLIOTECARIO")
def simular_atraso(id_emp):
    """MODO DEMO: vence o prazo do empréstimo (3 dias atrás) para testar a punição sem esperar."""
    if not app.config["MODO_DEMO"]:
        abort(404)
    emp = db.session.get(Emprestimo, id_emp)
    if emp and emp.status in ABERTOS:
        emp.data_prevista_devolucao = agora() - timedelta(days=3)
        emp.status = "ATRASADO"
        db.session.commit()
    flash("Prazo vencido simulado (modo demonstração). Registre a devolução para ver a punição.", "warning")
    return redirect(url_for("devolucoes"))


# ----------------------------------------------------------------------------
# Relatórios (UC-04, UC-13)
# ----------------------------------------------------------------------------
@app.route("/relatorios")
@roles_required("BIBLIOTECARIO", "ALUNO", "PROFESSOR")
def relatorios():
    atualizar_atrasados()
    proprio = session["tipo"] in LEITORES            # aluno/professor veem apenas os próprios registros
    q_emp = Emprestimo.query.filter(Emprestimo.status.in_(ABERTOS))
    q_adv = Advertencia.query
    if proprio:
        q_emp = q_emp.filter(Emprestimo.id_usuario == g.usuario.id_usuario)
        q_adv = q_adv.filter(Advertencia.id_usuario == g.usuario.id_usuario)
    abertos = q_emp.order_by(Emprestimo.data_prevista_devolucao).all()
    advs = q_adv.order_by(Advertencia.id_advertencia.desc()).all()
    return render_template("relatorios.html", atrasados=[e for e in abertos if e.status == "ATRASADO"],
                           em_dia=[e for e in abertos if e.status == "ATIVO"], advs=advs, proprio=proprio)


if __name__ == "__main__":
    if ARGS.reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[BibliotecaRB] --reset: banco removido ({DB_PATH})", flush=True)
    init_db()
    print(f"[BibliotecaRB] Modo demonstração: {'LIGADO' if app.config['MODO_DEMO'] else 'DESLIGADO'}", flush=True)
    print("[BibliotecaRB] Servidor em http://127.0.0.1:5000  (Ctrl+C para encerrar)", flush=True)
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
