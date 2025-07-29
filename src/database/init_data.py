"""
Initialize database with basic data for all tables.
"""
import asyncio
import logging
from src.database.connection import db_manager
from datetime import datetime

logger = logging.getLogger(__name__)

async def initialize_basic_data():
    """Initialize database with comprehensive basic data for all tables."""
    try:
        conn = await db_manager.get_connection()
        
        # Check if data already exists
        cursor = await conn.execute("SELECT COUNT(*) FROM Especialidades")
        count = (await cursor.fetchone())[0]
        
        if count > 0:
            logger.info("Database already has data, skipping initialization")
            await conn.close()
            return
            
        logger.info("Initializing database with comprehensive basic data...")
        
        # 1. Insert Especialidades (Specialties)
        specialties = [
            "Cardiologia", "Dermatologia", "Ortopedia", "Ginecologia", 
            "Pediatria", "Neurologia", "Psiquiatria", "Oftalmologia",
            "Urologia", "Endocrinologia", "Gastroenterologia", "Pneumologia",
            "Reumatologia", "Oncologia", "Radiologia", "Anestesiologia"
        ]
        
        logger.info("Inserting specialties...")
        for specialty in specialties:
            await conn.execute(
                "INSERT OR IGNORE INTO Especialidades (nome) VALUES (?)",
                (specialty,)
            )
        
        # 2. Insert Locais_Atendimento (Locations)
        locations = [
            ("Clínica Central", "Rua Principal, 123 - Centro - CEP: 70000-001"),
            ("Unidade Norte", "Av. Norte, 456 - Asa Norte - CEP: 70710-900"),
            ("Unidade Sul", "Rua Sul, 789 - Asa Sul - CEP: 70070-110"),
            ("Hospital Geral", "Av. Hospitalar, 321 - Setor Hospitalar - CEP: 70200-000"),
            ("Clínica de Exames", "Quadra 15, Lote 20 - Taguatinga - CEP: 72010-150")
        ]
        
        logger.info("Inserting locations...")
        for name, address in locations:
            await conn.execute(
                "INSERT OR IGNORE INTO Locais_Atendimento (nome, endereco) VALUES (?, ?)",
                (name, address)
            )
        
        # 3. Insert Convenios (Insurance Plans)
        insurances = [
            "Particular",
            "SUS - Sistema Único de Saúde",
            "Unimed",
            "Bradesco Saúde",
            "Amil",
            "SulAmérica Saúde",
            "Golden Cross",
            "NotreDame Intermédica",
            "Hapvida",
            "Prevent Senior"
        ]
        
        logger.info("Inserting insurance plans...")
        for insurance in insurances:
            await conn.execute(
                "INSERT OR IGNORE INTO Convenios (nome) VALUES (?)",
                (insurance,)
            )
        
        # 4. Insert Tipos_Consulta (Appointment Types)
        appointment_types = [
            ("Primeira Consulta", 60),
            ("Retorno", 30),
            ("Consulta de Urgência", 45),
            ("Telemedicina", 30),
            ("Consulta Pré-Operatória", 45),
            ("Consulta Pós-Operatória", 30),
            ("Avaliação Clínica", 50),
            ("Consulta Preventiva", 40)
        ]
        
        logger.info("Inserting appointment types...")
        for description, duration in appointment_types:
            await conn.execute(
                "INSERT OR IGNORE INTO Tipos_Consulta (descricao, duracao_padrao_minutos) VALUES (?, ?)",
                (description, duration)
            )
        
        # 5. Insert Exames (Exams)
        exams = [
            ("Hemograma Completo", "Jejum de 12 horas", 15),
            ("Raio-X Tórax", "Não há preparo especial", 10),
            ("Ultrassonografia Abdominal", "Jejum de 8 horas", 30),
            ("Eletrocardiograma", "Não há preparo especial", 15),
            ("Ecocardiograma", "Não há preparo especial", 30),
            ("Tomografia Computadorizada", "Jejum de 4 horas", 45),
            ("Ressonância Magnética", "Remover objetos metálicos", 60),
            ("Mamografia", "Não usar desodorante", 20),
            ("Colonoscopia", "Preparo intestinal 24h antes", 90),
            ("Endoscopia Digestiva", "Jejum de 12 horas", 30),
            ("Densitometria Óssea", "Não tomar cálcio 24h antes", 25),
            ("Teste Ergométrico", "Roupa adequada para exercício", 45)
        ]
        
        logger.info("Inserting exams...")
        for name, instructions, duration in exams:
            await conn.execute(
                "INSERT OR IGNORE INTO Exames (nome, instrucoes_preparo, duracao_padrao_minutos) VALUES (?, ?, ?)",
                (name, instructions, duration)
            )
        
        # 6. Insert Medicos (Doctors)
        doctors = [
            ("Dr. João Silva Santos", "CRM12345-DF"),
            ("Dra. Maria Oliveira Costa", "CRM23456-DF"),
            ("Dr. Carlos Eduardo Lima", "CRM34567-DF"),
            ("Dra. Ana Paula Ferreira", "CRM45678-DF"),
            ("Dr. Roberto Alves Pereira", "CRM56789-DF"),
            ("Dra. Fernanda Gomes Rocha", "CRM67890-DF"),
            ("Dr. Paulo Ricardo Moura", "CRM78901-DF"),
            ("Dra. Juliana Santos Dias", "CRM89012-DF"),
            ("Dr. Ricardo Henrique Neves", "CRM90123-DF"),
            ("Dra. Patricia Costa Sousa", "CRM01234-DF")
        ]
        
        logger.info("Inserting doctors...")
        for name, document in doctors:
            await conn.execute(
                "INSERT OR IGNORE INTO Medicos (nome, documento_conselho) VALUES (?, ?)",
                (name, document)
            )
        
        # 7. Insert Pacientes (Sample Patients)
        patients = [
            ("José da Silva", "12345678901", "1980-05-15", "M"),
            ("Maria Santos", "23456789012", "1992-08-20", "F"),
            ("Carlos Oliveira", "34567890123", "1975-12-03", "M"),
            ("Ana Costa", "45678901234", "1988-03-10", "F"),
            ("Pedro Almeida", "56789012345", "1965-09-25", "M")
        ]
        
        logger.info("Inserting sample patients...")
        for name, cpf, birth_date, gender in patients:
            await conn.execute(
                "INSERT OR IGNORE INTO Pacientes (nome, cpf, data_nascimento, sexo) VALUES (?, ?, ?, ?)",
                (name, cpf, birth_date, gender)
            )
        
        # 8. Insert Contatos (Contacts) - For patients and doctors
        contacts = [
            # Patient contacts
            (1, "paciente", "telefone", "61987654321"),
            (1, "paciente", "email", "jose.silva@email.com"),
            (2, "paciente", "telefone", "61976543210"),
            (2, "paciente", "email", "maria.santos@email.com"),
            (3, "paciente", "telefone", "61965432109"),
            (4, "paciente", "telefone", "61954321098"),
            (4, "paciente", "email", "ana.costa@email.com"),
            (5, "paciente", "telefone", "61943210987"),
            
            # Doctor contacts
            (1, "medico", "telefone", "61999888777"),
            (1, "medico", "email", "dr.joao@clinica.com"),
            (2, "medico", "telefone", "61988777666"),
            (2, "medico", "email", "dra.maria@clinica.com"),
            (3, "medico", "telefone", "61977666555"),
            (4, "medico", "telefone", "61966555444"),
            (5, "medico", "telefone", "61955444333")
        ]
        
        logger.info("Inserting contacts...")
        for entity_id, entity_type, contact_type, value in contacts:
            await conn.execute(
                "INSERT OR IGNORE INTO Contatos (entidade_id, entidade_tipo, tipo, valor) VALUES (?, ?, ?, ?)",
                (entity_id, entity_type, contact_type, value)
            )
        
        # 9. Insert Medico_Especialidades (Doctor-Specialty relationships)
        doctor_specialties = [
            (1, 1),   # Dr. João - Cardiologia
            (1, 2),   # Dr. João - Dermatologia
            (2, 3),   # Dra. Maria - Ortopedia
            (2, 4),   # Dra. Maria - Ginecologia
            (3, 5),   # Dr. Carlos - Pediatria
            (3, 6),   # Dr. Carlos - Neurologia
            (4, 7),   # Dra. Ana - Psiquiatria
            (4, 8),   # Dra. Ana - Oftalmologia
            (5, 9),   # Dr. Roberto - Urologia
            (5, 10),  # Dr. Roberto - Endocrinologia
            (6, 1),   # Dra. Fernanda - Cardiologia
            (7, 11),  # Dr. Paulo - Gastroenterologia
            (8, 12),  # Dra. Juliana - Pneumologia
            (9, 13),  # Dr. Ricardo - Reumatologia
            (10, 14)  # Dra. Patricia - Oncologia
        ]
        
        logger.info("Inserting doctor-specialty relationships...")
        for doctor_id, specialty_id in doctor_specialties:
            await conn.execute(
                "INSERT OR IGNORE INTO Medico_Especialidades (id_medico, id_especialidade) VALUES (?, ?)",
                (doctor_id, specialty_id)
            )
        
        # 10. Insert Medico_Convenios (Doctor-Insurance relationships)
        doctor_insurances = [
            (1, 1), (1, 2), (1, 3),  # Dr. João aceita Particular, SUS, Unimed
            (2, 1), (2, 3), (2, 4),  # Dra. Maria aceita Particular, Unimed, Bradesco
            (3, 1), (3, 2), (3, 5),  # Dr. Carlos aceita Particular, SUS, Amil
            (4, 1), (4, 6), (4, 7),  # Dra. Ana aceita Particular, SulAmérica, Golden Cross
            (5, 1), (5, 2), (5, 8),  # Dr. Roberto aceita Particular, SUS, NotreDame
            (6, 1), (6, 3), (6, 9),  # Dra. Fernanda aceita Particular, Unimed, Hapvida
            (7, 1), (7, 4), (7, 10), # Dr. Paulo aceita Particular, Bradesco, Prevent Senior
            (8, 1), (8, 2), (8, 5),  # Dra. Juliana aceita Particular, SUS, Amil
            (9, 1), (9, 6), (9, 7),  # Dr. Ricardo aceita Particular, SulAmérica, Golden Cross
            (10, 1), (10, 8), (10, 9) # Dra. Patricia aceita Particular, NotreDame, Hapvida
        ]
        
        logger.info("Inserting doctor-insurance relationships...")
        for doctor_id, insurance_id in doctor_insurances:
            await conn.execute(
                "INSERT OR IGNORE INTO Medico_Convenios (id_medico, id_convenio) VALUES (?, ?)",
                (doctor_id, insurance_id)
            )
        
        # 11. Insert Local_Exames (Location-Exam relationships)
        logger.info("Inserting location-exam relationships...")
        # All locations can perform basic exams
        basic_exams = [1, 2, 4, 8]  # Hemograma, Raio-X, ECG, Mamografia
        for location_id in range(1, 6):  # 5 locations
            for exam_id in basic_exams:
                await conn.execute(
                    "INSERT OR IGNORE INTO Local_Exames (id_local, id_exame) VALUES (?, ?)",
                    (location_id, exam_id)
                )
        
        # Specialized exams only in specific locations
        specialized_locations = [
            (4, [3, 5, 6, 7, 9, 10, 11, 12]),  # Hospital - advanced exams
            (5, [1, 2, 3, 4, 5, 6, 7, 8, 11, 12])  # Clínica de Exames - most exams
        ]
        
        for location_id, exam_ids in specialized_locations:
            for exam_id in exam_ids:
                await conn.execute(
                    "INSERT OR IGNORE INTO Local_Exames (id_local, id_exame) VALUES (?, ?)",
                    (location_id, exam_id)
                )
        
        # 12. Insert Sample Agendamentos (Appointments)
        sample_appointments = [
            # (id_paciente, id_local, id_convenio, id_tipo_consulta, id_exame, id_medico, data_hora_inicio, data_hora_fim, status, observacoes)
            (1, 1, 1, 1, None, 1, "2025-08-01 09:00:00", "2025-08-01 10:00:00", "agendado", "Primeira consulta cardiológica"),
            (2, 2, 3, 2, None, 2, "2025-08-01 14:00:00", "2025-08-01 14:30:00", "agendado", "Retorno ortopédico"),
            (3, 1, 2, 1, None, 3, "2025-08-02 08:00:00", "2025-08-02 09:00:00", "agendado", "Consulta pediátrica"),
            (4, 3, 1, 4, None, 4, "2025-08-02 15:00:00", "2025-08-02 15:30:00", "agendado", "Telemedicina - Psiquiatria"),
            (5, 4, 2, 1, None, 5, "2025-08-03 10:00:00", "2025-08-03 11:00:00", "agendado", "Consulta urológica"),
            
            # Exam appointments
            (1, 5, 1, None, 1, None, "2025-08-05 07:30:00", "2025-08-05 07:45:00", "agendado", "Hemograma de rotina"),
            (2, 4, 3, None, 2, None, "2025-08-05 08:00:00", "2025-08-05 08:10:00", "agendado", "Raio-X tórax"),
            (3, 5, 2, None, 4, None, "2025-08-06 09:00:00", "2025-08-06 09:15:00", "agendado", "ECG de rotina"),
        ]
        
        logger.info("Inserting sample appointments...")
        for appointment_data in sample_appointments:
            await conn.execute(
                """INSERT OR IGNORE INTO Agendamentos 
                   (id_paciente, id_local, id_convenio, id_tipo_consulta, id_exame, id_medico, 
                    data_hora_inicio, data_hora_fim, status, observacoes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                appointment_data
            )
        
        # Commit all changes
        await conn.commit()
        await conn.close()
        
        logger.info("✅ Database initialized with comprehensive basic data successfully")
        logger.info("📊 Data inserted:")
        logger.info(f"   • {len(specialties)} specialties")
        logger.info(f"   • {len(locations)} locations")
        logger.info(f"   • {len(insurances)} insurance plans")
        logger.info(f"   • {len(appointment_types)} appointment types")
        logger.info(f"   • {len(exams)} exams")
        logger.info(f"   • {len(doctors)} doctors")
        logger.info(f"   • {len(patients)} sample patients")
        logger.info(f"   • {len(contacts)} contacts")
        logger.info(f"   • {len(doctor_specialties)} doctor-specialty relationships")
        logger.info(f"   • {len(doctor_insurances)} doctor-insurance relationships")
        logger.info(f"   • {len(sample_appointments)} sample appointments")
        
    except Exception as e:
        logger.error(f"❌ Error initializing basic data: {e}")
        if 'conn' in locals():
            await conn.close()
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(initialize_basic_data())
