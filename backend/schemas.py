# Arquivo: backend/schemas.py
"""
Módulo de Schemas (Pydantic) - Os "Contratos" da API.

Este arquivo define os "contratos" de dados (schemas) que o Pydantic
usa para validar requisições (dados de entrada) e formatar
respostas (dados de saída).

Isso garante que nenhum dado mal formatado entre no nosso sistema
e que os dados enviados ao frontend estejam sempre consistentes.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- 1. SCHEMAS PARA O DASHBOARD ---

class CategoriaDetalhada(BaseModel):
    """
    Schema auxiliar para dados agrupados (usado por Dashboard e Reports).
    Representa o resultado de uma query 'group_by' com agregação.
    """
    nome_categoria: str
    valor_total: decimal.Decimal
    total_compras: int # (Para receitas, isso é 'total_registros')
    cor: str

class DashboardData(BaseModel):
    """Schema de RESPOSTA para o endpoint /dashboard/."""
    total_receitas: decimal.Decimal
    total_gastos: decimal.Decimal
    lucro_liquido: decimal.Decimal
    gastos_por_categoria: List[CategoriaDetalhada] 
    receitas_por_categoria: List[CategoriaDetalhada]


# --- 2. SCHEMAS PARA AUTENTICAÇÃO (Tokens) ---

class Token(BaseModel):
    """Schema de RESPOSTA para o endpoint /token."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Define os dados internos que são armazenados DENTRO do Token JWT.
    (Especificamente, o 'sub' (subject) do token).
    """
    nome_usuario: Optional[str] = None


# --- 3. SCHEMAS PARA USUÁRIO ---

class UsuarioCreate(BaseModel):
    """Schema de ENTRADA (criação) para um novo usuário."""
    nome_usuario: str
    senha: str # Recebe a senha em texto plano (será hasheada pelo 'crud.py')

class Usuario(BaseModel):
    """Schema de RESPOSTA (leitura) para um usuário."""
    id: int
    nome_usuario: str
    criado_em: datetime
    
    # Campos de Perfil (V7.0+)
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    
    # 'EmailStr' é um tipo do Pydantic que valida o formato do email.
    email: Optional[EmailStr] = None 

    # 'model_config' (Pydantic V2) permite que o schema
    # seja criado a partir de um objeto SQLAlchemy (ORM).
    model_config = {'from_attributes': True}


class UsuarioUpdate(BaseModel):
    """
    Schema de ENTRADA (atualização) para o perfil do usuário.
    Todos os campos são opcionais (lógica de PATCH).
    """
    nome_usuario: Optional[str] = None 
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None

class UsuarioChangePassword(BaseModel):
    """Schema de ENTRADA para alterar a senha."""
    senha_antiga: str
    senha_nova: str

# --- 4. SCHEMAS PARA CATEGORIA ---

class CategoriaCreate(BaseModel):
    """Schema de ENTRADA (criação) para uma nova categoria."""
    nome: str
    tipo: str # "Gasto" ou "Receita"
    cor: str = "#CCCCCC"

class Categoria(CategoriaCreate):
    """Schema de RESPOSTA (leitura) para uma categoria."""
    id: int
    # (Herda 'nome', 'tipo', 'cor' de CategoriaCreate)
    model_config = {'from_attributes': True}

class CategoriaUpdate(BaseModel):
    """
    Schema de ENTRADA (atualização) para uma categoria (PATCH).
    Todos os campos são opcionais.
    """
    nome: Optional[str] = None
    tipo: Optional[str] = None
    cor: Optional[str] = None

# --- 5. SCHEMAS PARA TRANSAÇÃO ---

class TransacaoCreate(BaseModel):
    """
    Schema de ENTRADA (criação/edição) para uma nova transação.
    É o que o formulário do modal envia.
    """
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    data: datetime # O frontend envia a string ISO (com data e hora)
    observacoes: str | None = None

class Transacao(TransacaoCreate):
    """Schema de RESPOSTA (leitura) para uma transação."""
    id: int
    usuario_id: int
    
    # 'categoria' é preenchido pelo 'joinedload' no 'crud.py'
    # (graças ao 'model_config' e 'relationship' no 'models.py')
    categoria: Categoria 
    
    model_config = {'from_attributes': True}
    
# --- 6. SCHEMAS PARA RELATÓRIOS ---

class PontoDeTendencia(BaseModel):
    """Representa um único ponto (X, Y) no gráfico de linha."""
    # (Aceita 'date' do agrupamento por dia ou 'str' do agrupamento por hora)
    data: date | str
    valor: decimal.Decimal

class DadosDeTendencia(BaseModel):
    """A resposta completa para o gráfico de tendências."""
    receitas: List[PontoDeTendencia]
    despesas: List[PontoDeTendencia]