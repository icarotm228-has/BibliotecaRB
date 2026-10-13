"""Controller: orquestra DAOs e aplica as regras de negócio (RN-01, RN-02, RN-03)."""
import sqlite3
from datetime import datetime

from database.connection import transacao
from dao.usuario_dao import UsuarioDAO
from dao.livro_dao import LivroDAO
from dao.emprestimo_dao import EmprestimoDAO
from dao.advertencia_dao import AdvertenciaDAO
from dao.consulta_dao import ConsultaDAO
from models import Emprestimo, Advertencia, Exemplar
from security import gerar_hash, verificar_senha


class RegraNegocioError(Exception):
    """Violação de regra de negócio (mensagem pronta para exibir ao operador)."""


class BibliotecaController:

    # ---------- UC-01: login ----------
    def autenticar(self, identificador, senha):
        with transacao() as conn:
            u = UsuarioDAO(conn).buscar_por_identificador(identificador)
        if not u or not verificar_senha(senha, u.senha_hash):
            raise RegraNegocioError("Credenciais inválidas.")
        if u.status != "ATIVO":
            raise RegraNegocioError("Acesso suspenso. Procure a administração da biblioteca.")
        return u

    # ---------- Cadastros ----------
    def cadastrar_usuario(self, usuario, senha):
        """Salva aluno, professor ou bibliotecário. Retorna o id gerado."""
        usuario.senha_hash = gerar_hash(senha)
        try:
            with transacao() as conn:
                return UsuarioDAO(conn).inserir(usuario)
        except sqlite3.IntegrityError as e:
            raise RegraNegocioError(f"Cadastro duplicado ou inválido (CPF/matrícula/SIAPE): {e}") from e

    def cadastrar_livro_e_exemplares(self, livro, tombos):
        """Adiciona a obra e vincula seus tombos físicos. Retorna o id do livro."""
        try:
            with transacao() as conn:
                dao = LivroDAO(conn)
                id_livro = dao.inserir_livro(livro)
                for tombo in tombos:
                    dao.inserir_exemplar(Exemplar(tombo, id_livro))
                return id_livro
        except sqlite3.IntegrityError as e:
            raise RegraNegocioError(f"Tombo duplicado ou dados inválidos: {e}") from e

    def consultar_acervo(self, termo=""):
        with transacao() as conn:
            return LivroDAO(conn).buscar(termo)

    def alterar_status_usuario(self, id_admin, id_usuario, novo_status):
        """UC-07: suspender/reativar/inativar (somente ADMIN)."""
        with transacao() as conn:
            dao = UsuarioDAO(conn)
            admin = dao.buscar_por_id(id_admin)
            if not admin or admin.TIPO != "ADMIN":
                raise RegraNegocioError("Apenas o Administrador pode alterar o status de cadastros.")
            dao.atualizar_status(id_usuario, novo_status)

    # ---------- UC-09: empréstimo ----------
    def registrar_emprestimo(self, id_usuario, tombo_exemplar, id_bibliotecario, agora=None):
        agora = agora or datetime.now()
        with transacao() as conn:
            u_dao, l_dao, e_dao = UsuarioDAO(conn), LivroDAO(conn), EmprestimoDAO(conn)

            bib = u_dao.buscar_por_id(id_bibliotecario)
            if not bib or bib.TIPO != "BIBLIOTECARIO":
                raise RegraNegocioError("Operação permitida apenas a um Bibliotecário.")

            usuario = u_dao.buscar_por_id(id_usuario)
            if not usuario:
                raise RegraNegocioError("Usuário não encontrado.")
            if usuario.TIPO not in ("ALUNO", "PROFESSOR"):
                raise RegraNegocioError("Apenas alunos e professores podem pegar livros emprestados.")
            if not usuario.esta_ativo:                                   # RN-02
                raise RegraNegocioError(f"Usuário com status {usuario.status}: empréstimo não permitido.")

            e_dao.marcar_atrasados(agora)
            pendentes = e_dao.listar_pendentes_do_usuario(id_usuario)
            if any(p.status == "ATRASADO" for p in pendentes):           # RN-02
                raise RegraNegocioError("Empréstimo não permitido: usuário possui itens em atraso.")
            if usuario.COTA_MAXIMA is not None and len(pendentes) >= usuario.COTA_MAXIMA:   # RN-03
                raise RegraNegocioError(f"Cota máxima atingida ({usuario.COTA_MAXIMA} livros simultâneos).")

            exemplar = l_dao.buscar_exemplar(tombo_exemplar)
            if not exemplar:
                raise RegraNegocioError("Exemplar não encontrado.")
            if not exemplar.disponivel:
                raise RegraNegocioError(f"Exemplar indisponível (status {exemplar.status}).")

            prevista = Emprestimo.calcular_data_devolucao(usuario.TIPO, agora)   # RN-01
            emp = Emprestimo(id_usuario, tombo_exemplar, id_bibliotecario, agora, prevista)
            e_dao.inserir(emp)
            l_dao.atualizar_status_exemplar(tombo_exemplar, "EMPRESTADO")
            return emp

    # ---------- UC-10 / UC-12: devolução ----------
    def registrar_devolucao(self, tombo_exemplar, agora=None, danificado=False):
        """Devolve o exemplar; se houver atraso, gera advertência e suspende o usuário.
        Retorna (emprestimo, dias_de_atraso, advertencia_ou_None)."""
        agora = agora or datetime.now()
        with transacao() as conn:
            u_dao, l_dao, e_dao, a_dao = UsuarioDAO(conn), LivroDAO(conn), EmprestimoDAO(conn), AdvertenciaDAO(conn)

            emp = e_dao.buscar_pendente_por_tombo(tombo_exemplar)
            if not emp:
                raise RegraNegocioError("Nenhum empréstimo ativo para este tombo.")

            e_dao.concluir(emp.id_emprestimo, agora)
            l_dao.atualizar_status_exemplar(tombo_exemplar, "DANIFICADO" if danificado else "DISPONIVEL")

            atraso, adv = emp.dias_de_atraso(agora), None
            if atraso > 0:
                adv = Advertencia(emp.id_usuario, emp.id_emprestimo,
                                  f"Devolução do exemplar {tombo_exemplar} com {atraso} dia(s) de atraso",
                                  dias_suspensao=atraso)
                a_dao.inserir(adv)
                u_dao.atualizar_status(emp.id_usuario, "SUSPENSO")
            return emp, atraso, adv

    # ---------- Consultas para as telas (UC-02, UC-04, UC-13) ----------
    def buscar_usuario(self, identificador):
        """Localiza por e-mail, matrícula ou SIAPE."""
        with transacao() as conn:
            return UsuarioDAO(conn).buscar_por_identificador(identificador.strip())

    def _atualizar_atrasos(self):
        with transacao() as conn:
            EmprestimoDAO(conn).marcar_atrasados(datetime.now())

    def listar_usuarios(self):
        with transacao() as conn:
            return ConsultaDAO(conn).listar_usuarios()

    def listar_acervo(self, termo=""):
        return [dict(r) for r in self.consultar_acervo(termo)]

    def listar_emprestimos(self, pendentes=False, id_usuario=None):
        self._atualizar_atrasos()
        with transacao() as conn:
            return ConsultaDAO(conn).listar_emprestimos(pendentes, id_usuario)

    def listar_advertencias(self, id_usuario=None):
        with transacao() as conn:
            return ConsultaDAO(conn).listar_advertencias(id_usuario)

    def metricas(self):
        self._atualizar_atrasos()
        with transacao() as conn:
            return ConsultaDAO(conn).metricas()
