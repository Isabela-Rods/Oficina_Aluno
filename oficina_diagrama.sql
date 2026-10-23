-- ============================================================
-- oficina_diagrama.sql — SOMENTE ESTRUTURA (sem dados)
-- Use este arquivo para gerar o Diagrama Entidade-Relacionamento:
--
--   MySQL Workbench > File > New Model
--   > File > Import > Reverse Engineer MySQL Create Script...
--   > escolha este arquivo > Next > Execute > Finish
--   > duplo clique em "EER Diagram" (as linhas das chaves estrangeiras
--     aparecem automaticamente) > File > Export > Export as PNG/PDF
-- ============================================================

CREATE SCHEMA IF NOT EXISTS oficina_db
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE oficina_db;

-- ============================================================
-- TABELA DE USUÁRIOS
-- Quem pode acessar o sistema (login).
-- A senha NUNCA é guardada em texto puro: ficam o salt e o
-- hash SHA-256 de (salt + senha).
-- ============================================================
CREATE TABLE usuario (
    id_usuario INT          NOT NULL AUTO_INCREMENT,   -- Identificador único (PK)
    nome       VARCHAR(100) NOT NULL,                  -- Nome exibido na tela principal
    login      VARCHAR(50)  NOT NULL,                  -- Nome de login
    salt       VARCHAR(32)  NOT NULL,                  -- Valor aleatório por usuário
    senha_hash CHAR(64)     NOT NULL,                  -- SHA-256(salt + senha) em hexadecimal
    CONSTRAINT pk_usuario       PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuario_login UNIQUE (login)         -- Login não pode repetir
);

-- ============================================================
-- TABELA DE DONOS (donos dos carros)
-- O CPF é DADO SENSÍVEL (LGPD): fica CRIPTOGRAFADO (AES) no banco.
-- Por isso o tipo é VARBINARY (bytes cifrados) e não VARCHAR.
-- ============================================================
CREATE TABLE dono (
    id_dono  INT            NOT NULL AUTO_INCREMENT,   -- Identificador único (PK)
    nome     VARCHAR(100)   NOT NULL,
    cpf      VARBINARY(255) NOT NULL,                  -- CPF criptografado com AES
    endereco VARCHAR(200)   NOT NULL,
    celular  VARCHAR(20)    NOT NULL,
    CONSTRAINT pk_dono     PRIMARY KEY (id_dono),
    CONSTRAINT uq_dono_cpf UNIQUE (cpf)                -- Evita dono duplicado (mesmo CPF)
);

-- ============================================================
-- TABELA DE CARROS
-- Todo carro pertence a UM dono (id_dono é obrigatório: NOT NULL).
-- ON DELETE RESTRICT: não permite excluir um dono que ainda tenha carros.
-- ============================================================
CREATE TABLE carro (
    id_carro INT         NOT NULL AUTO_INCREMENT,      -- Identificador único (PK)
    modelo   VARCHAR(80) NOT NULL,
    marca    VARCHAR(30) NOT NULL,
    placa    VARCHAR(7)  NOT NULL,                     -- ABC1234 ou ABC1D23 (Mercosul)
    ano      SMALLINT    NOT NULL,                     -- Ano de fabricação
    id_dono  INT         NOT NULL,                     -- FK -> dono
    CONSTRAINT pk_carro       PRIMARY KEY (id_carro),
    CONSTRAINT uq_carro_placa UNIQUE (placa),          -- Evita carro duplicado (mesma placa)
    CONSTRAINT fk_carro_dono  FOREIGN KEY (id_dono)
        REFERENCES dono (id_dono)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- ============================================================
-- TABELA DE PROCEDIMENTOS
-- Cada procedimento é de UM carro (e, por consequência, do dono do carro)
-- e registra o usuário que o cadastrou.
-- UNIQUE (id_carro, data_hora): o mesmo carro não pode ter dois
-- procedimentos no mesmo horário (evita duplicidade).
-- ============================================================
CREATE TABLE procedimento (
    id_procedimento INT          NOT NULL AUTO_INCREMENT,   -- Identificador único (PK)
    data_hora       DATETIME     NOT NULL,                  -- Dia e hora do procedimento
    descricao       VARCHAR(150) NOT NULL,                  -- Ex.: Troca de óleo, Revisão de freios
    status          ENUM('AGENDADO','REALIZADO','CANCELADO') NOT NULL DEFAULT 'AGENDADO',
    id_carro        INT          NOT NULL,                  -- FK -> carro
    id_usuario      INT          NOT NULL,                  -- FK -> usuario (quem registrou)
    CONSTRAINT pk_procedimento       PRIMARY KEY (id_procedimento),
    CONSTRAINT uq_carro_horario      UNIQUE (id_carro, data_hora),
    CONSTRAINT fk_procedimento_carro FOREIGN KEY (id_carro)
        REFERENCES carro (id_carro)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_procedimento_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
