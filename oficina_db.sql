DROP DATABASE IF EXISTS oficina_db;
CREATE DATABASE oficina_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Seleciona o banco recém-criado
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

-- ============================================================
-- CHAVE DE CRIPTOGRAFIA DO CPF
-- Variável de sessão usada apenas por este script.
-- PRECISA ser IGUAL à CHAVE_CRIPTOGRAFIA do arquivo sistema/config.py,
-- senão o sistema não consegue descriptografar os CPFs.
-- ============================================================
SET @chave = 'chave_saep_2025';

-- ============================================================
-- POPULAÇÃO (dados GENÉRICOS: substitua os "XX" pelos seus)
-- ============================================================

-- ---- usuario (senha = SHA-256 de salt + senha) ---------------------
-- Senhas de teste:  usuario1 / senha123
--                   usuario2 / senha123
--                   usuario3 / senha123
-- Exemplo: ('Administrador',     'admin',       '3f9a1c7e5b2d4086', SHA2(CONCAT('3f9a1c7e5b2d4086', 'admin123'), 256)),
INSERT INTO usuario (nome, login, salt, senha_hash) VALUES
  ('Ignacio',   'Ignacio', '3f9a1c7e5b2d4086', SHA2(CONCAT('3f9a1c7e5b2d4086', 'senha123'), 256)),
  ('Denis', 'Denis', '8c2e6a0b91d7f453', SHA2(CONCAT('8c2e6a0b91d7f453', 'senha123'), 256)),
  ('Administrador',  'Admin', 'd41b7e3a96c05f28', SHA2(CONCAT('d41b7e3a96c05f28', 'senha123'), 256));

-- ---- dono (CPFs de teste válidos, gravados criptografados) ---------
-- O dono 4 NÃO tem carros: serve para testar a exclusão de dono.
-- Exemplo: ('Mariana Souza',  AES_ENCRYPT('52998224725', @chave), 'Rua das Flores, 120 - Centro, São Paulo/SP',     '11987654321'),
INSERT INTO dono (nome, cpf, endereco, celular) VALUES
  ('Maria', AES_ENCRYPT('52998224725', @chave), 'Rua Senai, 300 - Bairro Centro, Cidade SP/SP', '11900000001'),
  ('Roberto', AES_ENCRYPT('11144477735', @chave), 'Rua da Vitória , 696 - Bairro Win, Cidade VI/VI', '11900000002'),
  ('Sabrina', AES_ENCRYPT('39053344705', @chave), 'Rua Maravilhosa, 10000 - Bairro dos sonhos, Cidade EUA/CA', '11900000003');

-- ---- carro (cada um associado a um dono existente) -----------------
-- Exemplo: ('Onix',    'Chevrolet',  'ABC1D23', 2020, 1),
INSERT INTO carro (modelo, marca, placa, ano, id_dono) VALUES
  ('Onix', 'Chevrolet', 'ABC1D23', 2026, 1),
  ('Ferrari purosangue', 'Ferrari', 'DEF4G56', 2025, 2),
  ('Urus', 'Lamborguini', 'GHI7J89', 2026, 3);

-- ---- procedimento --------------------------------------------------
-- Datas espalhadas em dias/meses diferentes e fora de ordem, para testar
-- a ordenação por data e o filtro por Dia / Mês / Ano na tela de procedimentos.
-- Exemplo: ('2026-10-08 09:00:00', 'Troca de óleo e filtros',     'AGENDADO',  1, 2),
INSERT INTO procedimento (data_hora, descricao, status, id_carro, id_usuario) VALUES
  ('2026-11-15 10:15:00', 'Troca de óleo e filtros', 'AGENDADO', 3, 3),
  ('2026-10-08 09:00:00', 'Troca de suspensão', 'AGENDADO', 1, 1),
  ('2026-10-08 14:30:00', 'Preventiva 10.000KM', 'AGENDADO', 2, 2);
