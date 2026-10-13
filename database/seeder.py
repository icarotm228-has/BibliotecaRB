"""Dados fictícios para testar o sistema imediatamente."""
from controllers.biblioteca_controller import BibliotecaController
from database.connection import transacao
from dao.usuario_dao import UsuarioDAO
from models import Administrador, Bibliotecario, Aluno, Professor, Livro


def popular_banco_inicial():
    """Insere 1 admin, 1 bibliotecário, 2 alunos, 1 professor, 3 livros (2 exemplares cada)
    e 1 empréstimo ativo. Só executa se o banco estiver vazio."""
    with transacao() as conn:
        if UsuarioDAO(conn).contar() > 0:
            return False
    c = BibliotecaController()
    c.cadastrar_usuario(Administrador("Admin Geral", "admin@rb.edu", "000.000.000-01"), "admin123")
    id_bib = c.cadastrar_usuario(Bibliotecario("Maria Bibliotecária", "bib@rb.edu", "000.000.000-02"), "bib123")
    id_joao = c.cadastrar_usuario(Aluno("João Silva", "joao@rb.edu", "000.000.000-03", "2024001", "Informática"), "123456")
    c.cadastrar_usuario(Aluno("Ana Souza", "ana@rb.edu", "000.000.000-04", "2024002", "Informática"), "123456")
    c.cadastrar_usuario(Professor("Prof. Carlos Lima", "carlos@rb.edu", "000.000.000-05", "SIAPE9001", "Matemática"), "123456")

    c.cadastrar_livro_e_exemplares(Livro("Dom Casmurro", "Machado de Assis", "9788535910663", "Romance", "Companhia das Letras"), ["T-0001", "T-0002"])
    c.cadastrar_livro_e_exemplares(Livro("Vidas Secas", "Graciliano Ramos", "9788501019295", "Romance", "Record"), ["T-0003", "T-0004"])
    c.cadastrar_livro_e_exemplares(Livro("Introdução à Física", "H. Moysés Nussenzveig", "9788521207450", "Ciências", "Blucher"), ["T-0005", "T-0006"])

    c.registrar_emprestimo(id_joao, "T-0002", id_bib)   # empréstimo ativo de teste
    return True
