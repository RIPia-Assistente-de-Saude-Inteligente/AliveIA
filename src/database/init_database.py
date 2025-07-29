"""
Script para criar e inicializar o banco de dados do sistema médico
"""

import sqlite3
import os
import asyncio
from pathlib import Path

def create_database():
    """Cria o banco de dados SQLite usando o arquivo database.sql"""
    
    # Caminhos baseados na estrutura do projeto
    db_path = Path(__file__).parent / "medical_system.db"
    sql_file = Path(__file__).parent / "database.sql"
    
    print(f"🏥 Inicializando Sistema de Banco de Dados Médico")
    print(f"📁 Banco: {db_path}")
    print(f"📄 SQL: {sql_file}")
    print("=" * 60)
    
    # Verificar se o arquivo SQL existe
    if not sql_file.exists():
        print(f"❌ Arquivo {sql_file} não encontrado!")
        return False
    
    try:
        # Conectar ao banco (cria se não existir)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗄️ Criando banco de dados...")
        
        # Ler e executar o arquivo SQL
        with open(sql_file, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # Executar script SQL
        cursor.executescript(sql_script)
        
        print("✅ Estrutura do banco criada com sucesso!")
        
        # Verificar tabelas criadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"📋 Tabelas criadas ({len(tables)}):")
        for table in tables:
            print(f"   • {table[0]}")
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar banco de dados: {e}")
        return False

def populate_initial_data():
    """Popula o banco com dados iniciais necessários"""
    
    db_path = Path(__file__).parent / "medical_system.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📝 Populando dados iniciais...")
        
        # Especialidades médicas
        especialidades = [
            ('Cardiologia',),
            ('Dermatologia',),
            ('Psicologia',),
            ('Neurologia',),
            ('Pediatria',),
            ('Ginecologia',),
            ('Ortopedia',),
            ('Oftalmologia',),
            ('Clínica Geral',),
            ('Psiquiatria',)
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Especialidades (nome) VALUES (?)",
            especialidades
        )
        
        # Médicos
        medicos = [
            ('Dr. João Cardoso', 'CRM12345-SP'),
            ('Dra. Maria Silva', 'CRM23456-SP'),
            ('Dr. Pedro Santos', 'CRP34567-SP'),
            ('Dra. Ana Costa', 'CRM45678-SP'),
            ('Dr. Carlos Oliveira', 'CRM56789-SP'),
            ('Dra. Lucia Fernandes', 'CRM67890-SP')
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Medicos (nome, documento_conselho) VALUES (?, ?)",
            medicos
        )
        
        # Locais de Atendimento
        locais = [
            ('Clínica Central', 'Rua das Flores, 123 - Centro, São Paulo - SP'),
            ('Hospital São José', 'Av. Brasil, 456 - Jardins, São Paulo - SP'),
            ('Clínica Norte', 'Rua da Paz, 789 - Vila Nova, São Paulo - SP'),
            ('Centro Médico Sul', 'Av. das Nações, 321 - Brooklin, São Paulo - SP')
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Locais_Atendimento (nome, endereco) VALUES (?, ?)",
            locais
        )
        
        # Convênios
        convenios = [
            ('SUS',),
            ('Unimed',),
            ('SulAmérica',),
            ('Bradesco Saúde',),
            ('Amil',),
            ('Particular',)
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Convenios (nome) VALUES (?)",
            convenios
        )
        
        # Tipos de Consulta
        tipos_consulta = [
            ('Primeira Consulta', 60),
            ('Retorno', 30),
            ('Consulta Urgente', 45),
            ('Telemedicina', 30),
            ('Consulta de Rotina', 40)
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Tipos_Consulta (descricao, duracao_padrao_minutos) VALUES (?, ?)",
            tipos_consulta
        )
        
        # Exames
        exames = [
            ('Hemograma Completo', 'Jejum de 8 horas', 15),
            ('Raio-X Tórax', 'Nenhum preparo necessário', 10),
            ('Eletrocardiograma', 'Nenhum preparo necessário', 20),
            ('Ultrassom Abdominal', 'Jejum de 6 horas', 30),
            ('Ressonância Magnética', 'Remover objetos metálicos', 45),
            ('Tomografia Computadorizada', 'Jejum de 4 horas', 25)
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Exames (nome, instrucoes_preparo, duracao_padrao_minutos) VALUES (?, ?, ?)",
            exames
        )
        
        # Relacionar médicos com especialidades
        medico_especialidades = [
            (1, 1),  # Dr. João Cardoso - Cardiologia
            (2, 2),  # Dra. Maria Silva - Dermatologia
            (3, 3),  # Dr. Pedro Santos - Psicologia
            (4, 4),  # Dra. Ana Costa - Neurologia
            (5, 9),  # Dr. Carlos Oliveira - Clínica Geral
            (6, 5)   # Dra. Lucia Fernandes - Pediatria
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Medico_Especialidades (id_medico, id_especialidade) VALUES (?, ?)",
            medico_especialidades
        )
        
        # Relacionar médicos com convênios (todos aceitam SUS e Particular)
        medico_convenios = []
        for medico_id in range(1, 7):  # 6 médicos
            medico_convenios.extend([
                (medico_id, 1),  # SUS
                (medico_id, 6),  # Particular
                (medico_id, 2),  # Unimed
            ])
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Medico_Convenios (id_medico, id_convenio) VALUES (?, ?)",
            medico_convenios
        )
        
        # Relacionar exames com locais
        local_exames = []
        for local_id in range(1, 5):  # 4 locais
            for exame_id in range(1, 7):  # 6 exames
                local_exames.append((local_id, exame_id))
        
        cursor.executemany(
            "INSERT OR IGNORE INTO Local_Exames (id_local, id_exame) VALUES (?, ?)",
            local_exames
        )
        
        conn.commit()
        conn.close()
        
        print("✅ Dados iniciais inseridos com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao popular dados: {e}")
        return False

def show_database_summary():
    """Mostra resumo do banco de dados criado"""
    
    db_path = Path(__file__).parent / "medical_system.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📊 RESUMO DO BANCO DE DADOS:")
        print("=" * 50)
        
        # Contar registros em cada tabela principal
        tables_to_check = [
            ('Pacientes', 'pacientes'),
            ('Especialidades', 'especialidades médicas'),
            ('Medicos', 'médicos'),
            ('Locais_Atendimento', 'locais de atendimento'),
            ('Convenios', 'convênios'),
            ('Tipos_Consulta', 'tipos de consulta'),
            ('Exames', 'exames'),
            ('Agendamentos', 'agendamentos')
        ]
        
        for table, description in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   📋 {description.title()}: {count}")
        
        conn.close()
        
        print(f"\n🎯 Banco de dados pronto para uso!")
        print(f"📁 Localização: {db_path}")
        
    except Exception as e:
        print(f"❌ Erro ao consultar banco: {e}")

if __name__ == "__main__":
    if create_database():
        if populate_initial_data():
            show_database_summary()
            print("\n🚀 Sistema pronto para inicializar!")
        else:
            print("\n⚠️  Banco criado, mas erro ao popular dados")
    else:
        print("\n❌ Falha ao criar banco de dados")
