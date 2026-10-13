# BibliotecaRB

Sistema web de gestão de biblioteca escolar (empréstimos, devoluções, acervo e usuários), desenvolvido como projeto da disciplina de Engenharia de Software I — IFPA, Campus Tucuruí.

## Funcionalidades
- **Administrador:** cadastra alunos, professores e bibliotecários; suspende e reativa cadastros.
- **Bibliotecário:** cadastra livros e exemplares (tombos), registra empréstimos e devoluções, acompanha atrasos e advertências.
- **Aluno / Professor:** consulta o acervo, seus empréstimos e suas advertências.
- **Regras:** prazo de 14 dias (aluno) e 30 dias (professor); limite de livros por aluno; devolução atrasada gera advertência e suspende o usuário.

## Tecnologias
Python 3 · Flask · Flask-SQLAlchemy (SQLite) · Jinja2 · Tailwind CSS (CDN)

## Como executar
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Acesse http://127.0.0.1:5000. Na primeira execução o banco (`database/bibliotecarb.db`) é criado e populado com dados de teste.

Opções: `--demo` (liga o modo demonstração), `--reset` (recria o banco), `--db caminho.db` (usa outro banco).

## Contas de teste
| Perfil | Login | Senha |
|---|---|---|
| Administrador | admin@rb.edu | admin123 |
| Bibliotecário | bib@rb.edu | bib123 |
| Aluno (ativo) | 2026001 | 123456 |
| Aluno (suspenso) | 2026002 | 123456 |

> Contas e senhas apenas para teste. Em uso real, defina a variável de ambiente `SECRET_KEY` e não use o modo demonstração.

## Estrutura
```
app.py              rotas, modelos (SQLAlchemy) e seeder
templates/          páginas HTML (Jinja2)
static/             CSS e JavaScript
database/schema.sql referência do esquema do banco
```

## Deploy no Render
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Variáveis de ambiente:** `SECRET_KEY` (valor aleatório), `ADMIN_SENHA` e `BIBLIOTECARIO_SENHA` (senhas dos usuários iniciais).

> No plano gratuito do Render o disco é temporário: o banco SQLite volta ao estado inicial a cada novo deploy ou reinício. Para guardar os dados, use um disco persistente (`BIBLIOTECARB_DB=/var/data/bibliotecarb.db`) ou um banco PostgreSQL.
