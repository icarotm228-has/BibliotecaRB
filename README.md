# BibliotecaRB

Sistema web de gestão de biblioteca escolar (acervo, empréstimos, devoluções e usuários), desenvolvido como projeto da disciplina de Engenharia de Software I — IFPA, Campus Tucuruí.

**Aplicação publicada:** https://SEU-APP.onrender.com *(substitua pelo endereço do Render)*
**Repositório:** https://github.com/icarotm228-has/BibliotecaRB

> No plano gratuito do Render o serviço "dorme" após alguns minutos sem acessos; o primeiro acesso pode levar cerca de 1 minuto.

## Funcionalidades
- **Administrador:** cadastra alunos, professores e bibliotecários; suspende e reativa cadastros.
- **Bibliotecário:** cadastra livros e exemplares (tombos), registra empréstimos e devoluções, acompanha atrasos e advertências.
- **Aluno / Professor:** consulta o acervo, seus empréstimos e suas advertências.

## Regras de negócio
- Prazo de devolução: 14 dias (aluno) e 30 dias (professor).
- Limite de livros emprestados ao mesmo tempo por aluno (constante `COTA` em `app.py`).
- Usuário suspenso ou com livro atrasado não pode fazer novos empréstimos.
- Devolução atrasada gera uma advertência e suspende o usuário; o Administrador reativa o cadastro.

## Tecnologias
Python 3 · Flask · Flask-SQLAlchemy (SQLite) · Jinja2 · Tailwind CSS (CDN) · Gunicorn

## Como executar localmente
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Acesse http://127.0.0.1:5000. Se o banco (`database/bibliotecarb.db`) não existir, ele é criado e populado com dados fictícios de teste.

Opções: `--reset` (recria o banco com os dados de teste), `--db caminho.db` (usa outro banco) e `--demo` (modo demonstração).

## Contas de teste
Os dados são fictícios. As senhas não ficam neste repositório: são informadas ao docente na documentação do projeto (seção 17.2). Em um banco novo, as senhas do Administrador e do Bibliotecário podem ser definidas pelas variáveis de ambiente `ADMIN_SENHA` e `BIBLIOTECARIO_SENHA`.

| Perfil | Login |
|---|---|
| Administrador | admin@rb.edu |
| Bibliotecário | bib@rb.edu |
| Aluno (ativo) | 2026001 |
| Aluno (suspenso) | 2026002 |

## Modo demonstração
Desligado por padrão. Quando ligado (`--demo` ou `DEMO_MODE=1`), permite trocar de perfil sem senha e mostra o botão "Simular atraso", usado para apresentar a advertência e a suspensão sem esperar o prazo. Não deixe ligado em um site público.

## Executável para Windows (.exe)
Gera um único arquivo que abre o sistema no navegador sem terminal e sem Python instalado (a máquina que **gera** o arquivo precisa do Python e de internet).

1. Instale o Python 3 no Windows e baixe o projeto.
2. Dê duplo clique em `build_exe.bat` (ou rode `build_exe.bat` no Prompt de Comando, na pasta do projeto).
3. O arquivo fica em `dist\BibliotecaRB.exe`. Copie-o para qualquer pasta e dê duplo clique.

Ao abrir, o programa cria `database\bibliotecarb.db` (e `bibliotecarb.log`) **ao lado do .exe** e abre o navegador em http://127.0.0.1:5000. Os dados ficam guardados entre uma execução e outra; para levá-los a outro computador, copie a pasta `database`. Para encerrar, entre como Administrador ou Bibliotecário e clique em **Encerrar sistema**.

Observações:
- O visual usa o Tailwind por CDN: o computador que executa precisa de internet.
- O Windows Defender/SmartScreen pode alertar sobre arquivos desconhecidos: clique em "Mais informações" e "Executar assim mesmo".
- O primeiro início do arquivo único pode levar alguns segundos.

## Deploy no Render
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Variáveis de ambiente:** `SECRET_KEY` (valor aleatório), `ADMIN_SENHA` e `BIBLIOTECARIO_SENHA`.
- `GET /healthz` informa se o app consegue acessar o banco.

O banco SQLite vai junto com o código (`database/bibliotecarb.db`). No plano gratuito o disco é temporário: a cada reinício ou novo deploy os dados voltam ao estado enviado ao GitHub, e o que foi cadastrado pelo site se perde.

## Limitações conhecidas
- A suspensão por atraso não termina sozinha; é preciso reativar o cadastro.
- Não há edição de usuários e livros, troca ou recuperação de senha, nem renovação de empréstimo.
- O sistema não envia lembretes de devolução.
- Os dados cadastrados no plano gratuito do Render não são preservados (veja acima).

## Estrutura
```
app.py                 rotas, modelos (SQLAlchemy) e dados iniciais
templates/             páginas HTML (Jinja2)
static/                CSS e JavaScript
database/              banco SQLite e schema.sql (referência do esquema)
requirements.txt       dependências
Procfile               comando de inicialização (referência)
```
