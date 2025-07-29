import aiosqlite

class MedicalData:
    """
    Acessa o banco de dados para obter dados médicos,
    como especialidades e exames disponíveis.
    """
    def __init__(self, db_path: str = 'database.db'):
        self.db_path = db_path

    def get_specialties(self) -> list[str]:
        """Retorna a lista de especialidades disponíveis (versão síncrona)."""
        # Retorna uma lista padrão para evitar problemas de async
        return ["Cardiologia", "Dermatologia", "Ortopedia", "Ginecologia", "Pediatria", "Neurologia"]

    async def get_specialties_async(self) -> list[str]:
        """Retorna a lista de especialidades disponíveis do banco de dados (versão async)."""
        specialties = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT nome FROM Especialidades")
                rows = await cursor.fetchall()
                specialties = [row[0] for row in rows]
        except aiosqlite.Error as e:
            print(f"Database error: {e}")
            # Retorna uma lista padrão em caso de erro de acesso ao DB
            return ["Cardiologia", "Dermatologia", "Ortopedia", "Ginecologia", "Pediatria", "Neurologia"]
        return specialties

    async def is_valid_specialty(self, specialty_name: str) -> bool:
        """Verifica se uma especialidade é válida (case-insensitive)."""
        specialties = await self.get_specialties_async()
        return specialty_name.lower() in [s.lower() for s in specialties]

    def get_locations_by_specialty(self, specialty_name: str) -> list[dict]:
        """Retorna locais que atendem uma especialidade específica (versão síncrona)."""
        # Simulação de dados - em produção viria do banco
        locations_map = {
            "cardiologia": [
                {"id": 1, "nome": "Hospital São Paulo"},
                {"id": 2, "nome": "Clínica CardioVida"},
                {"id": 3, "nome": "Centro Médico Central"}
            ],
            "dermatologia": [
                {"id": 1, "nome": "Hospital São Paulo"},
                {"id": 4, "nome": "Clínica DermaBela"},
                {"id": 5, "nome": "Instituto de Dermatologia"}
            ],
            "ortopedia": [
                {"id": 2, "nome": "Clínica CardioVida"},
                {"id": 3, "nome": "Centro Médico Central"},
                {"id": 6, "nome": "Ortopedia Especializada"}
            ],
            "ginecologia": [
                {"id": 1, "nome": "Hospital São Paulo"},
                {"id": 7, "nome": "Clínica da Mulher"},
                {"id": 8, "nome": "Centro Ginecológico"}
            ],
            "pediatria": [
                {"id": 1, "nome": "Hospital São Paulo"},
                {"id": 3, "nome": "Centro Médico Central"},
                {"id": 9, "nome": "Clínica Infantil"}
            ],
            "neurologia": [
                {"id": 1, "nome": "Hospital São Paulo"},
                {"id": 3, "nome": "Centro Médico Central"},
                {"id": 10, "nome": "Instituto Neurológico"}
            ]
        }
        
        return locations_map.get(specialty_name.lower(), [])

    async def get_locations_by_specialty_async(self, specialty_name: str) -> list[dict]:
        """Retorna locais que atendem uma especialidade específica do banco (versão async)."""
        locations = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Query que busca locais através dos agendamentos de médicos com a especialidade
                query = """
                SELECT DISTINCT l.id_local, l.nome, l.endereco 
                FROM Locais_Atendimento l
                JOIN Agendamentos a ON a.id_local = l.id_local
                JOIN Medicos m ON m.id_medico = a.id_medico
                JOIN Medico_Especialidades me ON me.id_medico = m.id_medico
                JOIN Especialidades e ON me.id_especialidade = e.id_especialidade
                WHERE LOWER(e.nome) = LOWER(?)
                """
                cursor = await db.execute(query, (specialty_name,))
                rows = await cursor.fetchall()
                locations = [{"id": row[0], "nome": row[1], "endereco": row[2]} for row in rows]
                
                # Se não encontrar nenhum local através de agendamentos, retorna todos os locais
                if not locations:
                    cursor = await db.execute("SELECT id_local, nome, endereco FROM Locais_Atendimento")
                    rows = await cursor.fetchall()
                    locations = [{"id": row[0], "nome": row[1], "endereco": row[2]} for row in rows]
                    
        except aiosqlite.Error as e:
            print(f"Database error: {e}")
            # Fallback para dados simulados
            return self.get_locations_by_specialty(specialty_name)
        return locations

# Instância única para ser usada em todo o projeto
db = MedicalData()