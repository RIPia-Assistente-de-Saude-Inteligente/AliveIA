class MedicalData:
    """
    Simula o acesso a um banco de dados com dados médicos,
    como especialidades e exames disponíveis.
    """
    def __init__(self):
        self._specialties = [
            "Cardiologia",
            "Dermatologia",
            "Ortopedia",
            "Ginecologia",
            "Pediatria"
        ]

    def get_specialties(self) -> list[str]:
        """Retorna a lista de especialidades disponíveis."""
        return self._specialties

    def is_valid_specialty(self, specialty_name: str) -> bool:
        """Verifica se uma especialidade é válida (case-insensitive)."""
        return specialty_name.lower() in [s.lower() for s in self._specialties]

# Instância única para ser usada em todo o projeto
db = MedicalData()