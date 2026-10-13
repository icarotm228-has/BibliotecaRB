-- BibliotecaRB - schema SQLite (executado por database.connection.init_db)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tb_usuario (
    id_usuario   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    email        TEXT NOT NULL,
    cpf          TEXT NOT NULL UNIQUE,
    tipo_usuario TEXT NOT NULL CHECK (tipo_usuario IN ('ALUNO','PROFESSOR','BIBLIOTECARIO','ADMIN')),
    status       TEXT NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO','SUSPENSO')),
    matricula    TEXT UNIQUE,   -- alunos
    curso        TEXT,          -- alunos
    siape        TEXT UNIQUE,   -- professores
    departamento TEXT,          -- professores
    senha_hash   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tb_livro (
    id_livro  INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo    TEXT NOT NULL,
    autor     TEXT NOT NULL,
    isbn      TEXT NOT NULL,
    categoria TEXT NOT NULL,
    editora   TEXT
);

CREATE TABLE IF NOT EXISTS tb_exemplar (
    tombo    TEXT PRIMARY KEY,  -- código patrimonial único
    id_livro INTEGER NOT NULL REFERENCES tb_livro(id_livro),
    status   TEXT NOT NULL DEFAULT 'DISPONIVEL' CHECK (status IN ('DISPONIVEL','EMPRESTADO','DANIFICADO'))
);

CREATE TABLE IF NOT EXISTS tb_emprestimo (
    id_emprestimo           INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario              INTEGER NOT NULL REFERENCES tb_usuario(id_usuario),
    tombo_exemplar          TEXT    NOT NULL REFERENCES tb_exemplar(tombo),
    id_bibliotecario        INTEGER NOT NULL REFERENCES tb_usuario(id_usuario),
    data_emprestimo         DATETIME NOT NULL,
    data_prevista_devolucao DATETIME NOT NULL,
    data_devolucao_real     DATETIME,
    status                  TEXT NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO','CONCLUIDO','ATRASADO'))
);

CREATE TABLE IF NOT EXISTS tb_advertencia (
    id_advertencia INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario     INTEGER NOT NULL REFERENCES tb_usuario(id_usuario),
    id_emprestimo  INTEGER REFERENCES tb_emprestimo(id_emprestimo),
    motivo         TEXT NOT NULL,
    dias_suspensao INTEGER,
    data_ocorrencia DATETIME
);
