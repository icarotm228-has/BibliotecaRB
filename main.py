"""
BibliotecaRB - backend (Models, DAO, Database, Controllers). Só biblioteca padrão do Python 3.8+.

Como executar (na pasta do projeto):
    python main.py            # cria biblioteca.db, popula dados de teste e roda uma demonstração
    rm biblioteca.db          # (opcional) apaga o banco para recomeçar do zero
"""
import sqlite3
from datetime import datetime, timedelta

from database.connection import init_db, transacao, DB_PATH
from database.seeder import popular_banco_inicial
from controllers.biblioteca_controller import BibliotecaController, RegraNegocioError


def tentar(titulo, fn):
    """Executa uma operação e imprime o resultado ou a regra violada."""
    try:
        r = fn()
        print(f"[OK]   {titulo}")
        return r
    except RegraNegocioError as e:
        print(f"[ERRO] {titulo} -> {e}")


if __name__ == "__main__":
    init_db()
    print("Banco:", DB_PATH, "| populado agora:", popular_banco_inicial())
    c = BibliotecaController()
    ID_BIB, ID_JOAO, ID_ANA, ID_PROF = 2, 3, 4, 5   # ids criados pelo seeder

    print("\n--- Login ---")
    u = tentar("Login João (2024001)", lambda: c.autenticar("2024001", "123456"))
    tentar("Login com senha errada", lambda: c.autenticar("2024001", "errada"))

    print("\n--- Cota de 3 livros (João já tem 1 emprestado) ---")
    tentar("João pega T-0001", lambda: c.registrar_emprestimo(ID_JOAO, "T-0001", ID_BIB))
    tentar("João pega T-0003", lambda: c.registrar_emprestimo(ID_JOAO, "T-0003", ID_BIB))
    tentar("João pega T-0004 (4º livro)", lambda: c.registrar_emprestimo(ID_JOAO, "T-0004", ID_BIB))
    tentar("Ana pega T-0001 (já emprestado)", lambda: c.registrar_emprestimo(ID_ANA, "T-0001", ID_BIB))

    print("\n--- Prazo: professor 30 dias / aluno 14 dias ---")
    emp = tentar("Professor pega T-0006", lambda: c.registrar_emprestimo(ID_PROF, "T-0006", ID_BIB))
    print("       devolução prevista:", emp.data_prevista_devolucao.date(), "(30 dias)")

    print("\n--- Devolução com atraso -> advertência + suspensão ---")
    emp = tentar("Ana pega T-0005", lambda: c.registrar_emprestimo(ID_ANA, "T-0005", ID_BIB))
    futuro = datetime.now() + timedelta(days=17)    # simula passagem do tempo (prazo era 14 dias)
    r = tentar("Ana devolve T-0005 com 3 dias de atraso", lambda: c.registrar_devolucao("T-0005", agora=futuro))
    print("       atraso:", r[1], "dia(s) | advertência:", r[2].motivo)
    tentar("Ana tenta novo empréstimo (T-0005)", lambda: c.registrar_emprestimo(ID_ANA, "T-0005", ID_BIB))

    print("\n--- Reativação pelo admin e consulta ao acervo ---")
    tentar("Admin reativa Ana", lambda: c.alterar_status_usuario(1, ID_ANA, "ATIVO"))
    for r in c.consultar_acervo("Física"):
        print("       ", r["titulo"], "|", r["tombo"], "|", r["status"])
