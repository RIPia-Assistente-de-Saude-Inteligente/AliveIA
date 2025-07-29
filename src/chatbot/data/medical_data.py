import aiosqlite

class MedicalData:
    """
    Acessa o banco de dados para obter dados médicos,
    como especialidades e exames disponíveis.
    """
    def __init__(self, db_path: str = 'src/database/database.sql'):
        self.db_path = db_path

    def get_specialties(self) -> list[str]:
        """Retorna a lista de especialidades disponíveis (versão síncrona)."""
        # Retorna uma lista padrão para evitar problemas de async
        return ["Cardiologia", "Dermatologia", "Ortopedia", "Ginecologia", "Pediatria", "Neurologia"]

    async def get_specialties_async(self) -> list[str]:
        """Retorna a lista de especialidades disponíveis do banco de dados (versão async)."""
        specialties = []
        # O ideal é usar um pool de conexões em um app real
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT nome FROM Especialidades")
                rows = await cursor.fetchall()
                specialties = [row[0] for row in rows]
        except aiosqlite.Error as e:
            print(f"Database error: {e}")
            # Retorna uma lista padrão em caso de erro de acesso ao DB
            return ["Cardiologia", "Dermatologia", "Ortopedia"]
        return specialties

    async def is_valid_specialty(self, specialty_name: str) -> bool:
        """Verifica se uma especialidade é válida (case-insensitive)."""
        specialties = await self.get_specialties_async()
        return specialty_name.lower() in [s.lower() for s in specialties]

# Instância única para ser usada em todo o projeto
db = MedicalData()