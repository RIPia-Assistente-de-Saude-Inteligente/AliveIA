-- Habilita o suporte a chaves estrangeiras no SQLite.
PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------
-- TABELAS DE ENTIDADES PRINCIPAIS (versões anteriores)
-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS Pacientes (
    id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf TEXT(11) NOT NULL UNIQUE,
    data_nascimento TEXT NOT NULL,
    sexo TEXT CHECK(sexo IN ('M', 'F', 'O')) NOT NULL
);

CREATE TABLE IF NOT EXISTS Especialidades (
    id_especialidade INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Medicos (
    id_medico INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    documento_conselho TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Medico_Especialidades (
    id_medico INTEGER NOT NULL,
    id_especialidade INTEGER NOT NULL,
    PRIMARY KEY (id_medico, id_especialidade),
    FOREIGN KEY (id_medico) REFERENCES Medicos (id_medico) ON DELETE CASCADE,
    FOREIGN KEY (id_especialidade) REFERENCES Especialidades (id_especialidade) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Contatos (
    id_contato INTEGER PRIMARY KEY AUTOINCREMENT,
    entidade_id INTEGER NOT NULL,
    entidade_tipo TEXT NOT NULL CHECK(entidade_tipo IN ('paciente', 'medico')),
    tipo TEXT CHECK(tipo IN ('email', 'telefone', 'whatsapp')) NOT NULL,
    valor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Locais_Atendimento (
    id_local INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    endereco TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Convenios (
    id_convenio INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Medico_Convenios (
    id_medico INTEGER NOT NULL,
    id_convenio INTEGER NOT NULL,
    PRIMARY KEY (id_medico, id_convenio),
    FOREIGN KEY (id_medico) REFERENCES Medicos (id_medico) ON DELETE CASCADE,
    FOREIGN KEY (id_convenio) REFERENCES Convenios (id_convenio) ON DELETE CASCADE
);

-- ----------------------------------------------------------------
-- NOVAS TABELAS E MODIFICAÇÕES PARA EXAMES (Etapa 4)
-- ----------------------------------------------------------------

-- Tabela para os tipos de consulta (substitui a antiga Tipos_Agendamento para maior clareza).
CREATE TABLE IF NOT EXISTS Tipos_Consulta (
    id_tipo_consulta INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL UNIQUE, -- Ex: 'Primeira Consulta', 'Retorno', 'Telemedicina'
    duracao_padrao_minutos INTEGER NOT NULL
);

-- Tabela para definir os exames disponíveis.
CREATE TABLE IF NOT EXISTS Exames (
    id_exame INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE, -- Ex: 'Hemograma Completo', 'Raio-X do Tórax'
    instrucoes_preparo TEXT, -- Instruções como jejum, etc.
    duracao_padrao_minutos INTEGER NOT NULL
);

-- Tabela de ligação para definir quais exames podem ser realizados em quais locais.
CREATE TABLE IF NOT EXISTS Local_Exames (
    id_local INTEGER NOT NULL,
    id_exame INTEGER NOT NULL,
    PRIMARY KEY (id_local, id_exame),
    FOREIGN KEY (id_local) REFERENCES Locais_Atendimento (id_local) ON DELETE CASCADE,
    FOREIGN KEY (id_exame) REFERENCES Exames (id_exame) ON DELETE CASCADE
);

-- Tabela principal de agendamentos, agora modificada para aceitar consultas OU exames.
CREATE TABLE IF NOT EXISTS Agendamentos (
    id_agendamento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente INTEGER NOT NULL,
    id_local INTEGER NOT NULL,
    id_convenio INTEGER, -- Nulo se for particular.
    
    -- Um agendamento é para uma consulta OU para um exame.
    id_tipo_consulta INTEGER, -- Preenchido se for uma consulta.
    id_exame INTEGER,         -- Preenchido se for um exame.

    -- O médico pode ser o que executa a consulta ou o que analisa o exame. Pode ser nulo para exames simples.
    id_medico INTEGER,
    
    data_hora_inicio DATETIME NOT NULL,
    data_hora_fim DATETIME NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('agendado', 'cancelado', 'realizado', 'ausente')),
    observacoes TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Chaves estrangeiras
    FOREIGN KEY (id_paciente) REFERENCES Pacientes (id_paciente),
    FOREIGN KEY (id_local) REFERENCES Locais_Atendimento (id_local),
    FOREIGN KEY (id_convenio) REFERENCES Convenios (id_convenio),
    FOREIGN KEY (id_medico) REFERENCES Medicos (id_medico),
    FOREIGN KEY (id_tipo_consulta) REFERENCES Tipos_Consulta (id_tipo_consulta),
    FOREIGN KEY (id_exame) REFERENCES Exames (id_exame),

    -- Regra de negócio: Garante que um agendamento seja ou uma consulta ou um exame, mas não ambos.
    CHECK (
        (id_tipo_consulta IS NOT NULL AND id_exame IS NULL) OR 
        (id_tipo_consulta IS NULL AND id_exame IS NOT NULL)
    ),

    -- Garante que um mesmo médico não tenha dois eventos (consulta ou exame) no mesmo horário.
    UNIQUE (id_medico, data_hora_inicio)
);

-- ----------------------------------------------------------------
-- ÍNDICES FINAIS PARA OTIMIZAÇÃO
-- ----------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_contatos_entidade ON Contatos (entidade_id, entidade_tipo);
CREATE INDEX IF NOT EXISTS idx_medico_especialidades_medico ON Medico_Especialidades (id_medico);
CREATE INDEX IF NOT EXISTS idx_medico_especialidades_especialidade ON Medico_Especialidades (id_especialidade);
CREATE INDEX IF NOT EXISTS idx_local_exames_exame ON Local_Exames (id_exame);

-- Tabela Horarios_Disponiveis foi removida em favor de uma lógica mais dinâmica que pode ser
-- implementada na aplicação, mas pode ser adicionada de volta se a regra de negócio for estática.
-- Para este modelo final, a disponibilidade será calculada pela aplicação com base nos agendamentos existentes.

CREATE INDEX IF NOT EXISTS idx_agendamentos_paciente ON Agendamentos (id_paciente);
CREATE INDEX IF NOT EXISTS idx_agendamentos_medico_data ON Agendamentos (id_medico, data_hora_inicio);
CREATE INDEX IF NOT EXISTS idx_agendamentos_local_data ON Agendamentos (id_local, data_hora_inicio);