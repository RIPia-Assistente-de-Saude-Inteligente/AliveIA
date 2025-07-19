"""
Pydantic models for API request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums
class SexoEnum(str, Enum):
    MASCULINO = "M"
    FEMININO = "F"
    OUTRO = "O"

class TipoContatoEnum(str, Enum):
    EMAIL = "email"
    TELEFONE = "telefone"
    WHATSAPP = "whatsapp"

class EntidadeTipoEnum(str, Enum):
    PACIENTE = "paciente"
    MEDICO = "medico"

class StatusAgendamentoEnum(str, Enum):
    AGENDADO = "agendado"
    CANCELADO = "cancelado"
    REALIZADO = "realizado"
    AUSENTE = "ausente"

# Base models
class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: str = "Operação realizada com sucesso"

# Paciente models
class PacienteBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    cpf: str = Field(..., min_length=11, max_length=11)
    data_nascimento: str = Field(..., description="Data no formato YYYY-MM-DD")
    sexo: SexoEnum

class PacienteCreate(PacienteBase):
    pass

class PacienteUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    cpf: Optional[str] = Field(None, min_length=11, max_length=11)
    data_nascimento: Optional[str] = None
    sexo: Optional[SexoEnum] = None

class PacienteResponse(PacienteBase):
    id_paciente: int
    
    class Config:
        from_attributes = True

# Médico models
class MedicoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    documento_conselho: str = Field(..., min_length=1, max_length=20)

class MedicoCreate(MedicoBase):
    pass

class MedicoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    documento_conselho: Optional[str] = Field(None, min_length=1, max_length=20)

class MedicoResponse(MedicoBase):
    id_medico: int
    
    class Config:
        from_attributes = True

# Especialidade models
class EspecialidadeBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)

class EspecialidadeCreate(EspecialidadeBase):
    pass

class EspecialidadeResponse(EspecialidadeBase):
    id_especialidade: int
    
    class Config:
        from_attributes = True

# Contato models
class ContatoBase(BaseModel):
    entidade_id: int
    entidade_tipo: EntidadeTipoEnum
    tipo: TipoContatoEnum
    valor: str = Field(..., min_length=1, max_length=100)

class ContatoCreate(ContatoBase):
    pass

class ContatoResponse(ContatoBase):
    id_contato: int
    
    class Config:
        from_attributes = True

# Local de atendimento models
class LocalAtendimentoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    endereco: str = Field(..., min_length=5, max_length=200)

class LocalAtendimentoCreate(LocalAtendimentoBase):
    pass

class LocalAtendimentoResponse(LocalAtendimentoBase):
    id_local: int
    
    class Config:
        from_attributes = True

# Convênio models
class ConvenioBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)

class ConvenioCreate(ConvenioBase):
    pass

class ConvenioResponse(ConvenioBase):
    id_convenio: int
    
    class Config:
        from_attributes = True

# Tipo de consulta models
class TipoConsultaBase(BaseModel):
    descricao: str = Field(..., min_length=2, max_length=100)
    duracao_padrao_minutos: int = Field(..., gt=0, le=480)

class TipoConsultaCreate(TipoConsultaBase):
    pass

class TipoConsultaResponse(TipoConsultaBase):
    id_tipo_consulta: int
    
    class Config:
        from_attributes = True

# Exame models
class ExameBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    instrucoes_preparo: Optional[str] = None
    duracao_padrao_minutos: int = Field(..., gt=0, le=480)

class ExameCreate(ExameBase):
    pass

class ExameResponse(ExameBase):
    id_exame: int
    
    class Config:
        from_attributes = True

# Agendamento models
class AgendamentoBase(BaseModel):
    id_paciente: int
    id_local: int
    id_convenio: Optional[int] = None
    id_tipo_consulta: Optional[int] = None
    id_exame: Optional[int] = None
    id_medico: Optional[int] = None
    data_hora_inicio: datetime
    data_hora_fim: datetime
    status: StatusAgendamentoEnum = StatusAgendamentoEnum.AGENDADO
    observacoes: Optional[str] = None

class AgendamentoCreate(AgendamentoBase):
    pass

class AgendamentoUpdate(BaseModel):
    id_local: Optional[int] = None
    id_convenio: Optional[int] = None
    id_medico: Optional[int] = None
    data_hora_inicio: Optional[datetime] = None
    data_hora_fim: Optional[datetime] = None
    status: Optional[StatusAgendamentoEnum] = None
    observacoes: Optional[str] = None

class AgendamentoResponse(AgendamentoBase):
    id_agendamento: int
    data_criacao: datetime
    
    class Config:
        from_attributes = True

# Response with data
class PacientesListResponse(BaseResponse):
    data: List[PacienteResponse]
    total: int

class MedicosListResponse(BaseResponse):
    data: List[MedicoResponse]
    total: int

class AgendamentosListResponse(BaseResponse):
    data: List[AgendamentoResponse]
    total: int
