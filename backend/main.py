# Arquivo: backend/main.py
"""Módulo Principal da Aplicação FastAPI.

Inicializa a aplicação, configura os middlewares de segurança e registra todos
os endpoints da API.

Pontos de segurança implementados neste módulo:

- **CORS por allowlist explícita.** A configuração anterior usava a expressão
  `https?://(localhost(:\\d+)?|.*\\.vercel\\.app)` junto com
  `allow_credentials=True`: qualquer pessoa capaz de publicar um site em
  `*.vercel.app` (gratuito e instantâneo) podia ler os dados financeiros de um
  usuário autenticado a partir do navegador dele.
- **Schema do banco gerido por migrações.** O `create_all` no import foi
  removido; alterações de esquema passam pelo Alembic.
- **Respostas de erro genéricas.** Falhas internas não expõem stack trace nem
  mensagens do driver de banco ao cliente.
- **Validação de posse em todos os recursos.** Nenhum endpoint aceita um ID sem
  confirmar que o recurso pertence ao usuário autenticado.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import crud, schemas, security
from .core.config import descrever_configuracao, settings
from .core.logging import configurar_logging, obter_logger
from .core.middleware import (
    MiddlewareDeHeadersDeSeguranca,
    MiddlewareDeLogDeRequisicao,
    MiddlewareDeTamanhoDeCorpo,
)
from .dependencies import (
    Auditoria,
    SessaoDB,
    UsuarioAutenticado,
    rate_limit_cadastro,
    rate_limit_login,
)
from .schemas import MAXIMO_DIAS_POR_CONSULTA

configurar_logging(settings.LOG_LEVEL)
logger = obter_logger(__name__)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Gerencia a inicialização e o encerramento da aplicação.

    Args:
        app (FastAPI): A instância da aplicação.

    Yields:
        None: Durante o período em que a aplicação está ativa.
    """
    logger.info(
        "Iniciando a API de Controle Financeiro",
        extra={"configuracao": descrever_configuracao(settings)},
    )

    # O esquema do banco é responsabilidade do Alembic (`alembic upgrade head`).
    # Criar tabelas a partir do código em tempo de execução deixaria produção e
    # migrações fora de sincronia, sem histórico nem caminho de rollback.

    yield

    logger.info("Encerrando a API de Controle Financeiro")


# --- Configuração Inicial ---

app = FastAPI(
    title="NOMAD Controle Financeiro API",
    description="API para o aplicativo de controle financeiro NOMAD.",
    version="2.0.0",
    lifespan=ciclo_de_vida,
    # A documentação interativa revela toda a superfície da API; em produção
    # ela fica desativada por padrão.
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

# --- Middlewares ---
# A ordem importa: o Starlette executa os middlewares na ordem inversa do
# registro, então o último adicionado é o mais externo.

app.add_middleware(MiddlewareDeHeadersDeSeguranca)

app.add_middleware(
    CORSMiddleware,
    # Allowlist explícita, sem regex e sem curinga.
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    # Apenas os métodos efetivamente usados pela API.
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

app.add_middleware(
    MiddlewareDeTamanhoDeCorpo, tamanho_maximo=settings.MAX_REQUEST_BODY_BYTES
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

app.add_middleware(MiddlewareDeLogDeRequisicao)


# --- Tratadores de Exceção ---


@app.exception_handler(RequestValidationError)
async def tratar_erro_de_validacao(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Converte erros de validação em uma resposta 422 sem ecoar a entrada.

    O tratador padrão do FastAPI devolve o valor recebido dentro do campo
    `input`. Em um endpoint de senha isso significa refletir a senha enviada de
    volta ao cliente — e para dentro de qualquer log de resposta no caminho.

    Args:
        request (Request): A requisição que falhou na validação.
        exc (RequestValidationError): O erro de validação.

    Returns:
        JSONResponse: Resposta 422 com os campos problemáticos, sem os valores.
    """
    erros = [
        {
            "campo": ".".join(str(parte) for parte in erro.get("loc", [])),
            "mensagem": erro.get("msg", "Valor inválido."),
            "tipo": erro.get("type", "desconhecido"),
        }
        for erro in exc.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Dados inválidos na requisição.", "erros": erros},
    )


@app.exception_handler(crud.CategoriaInvalidaError)
async def tratar_categoria_invalida(
    request: Request, exc: crud.CategoriaInvalidaError
) -> JSONResponse:
    """Converte referência a categoria de terceiros em uma resposta 404.

    Responder 404 (e não 403) evita confirmar a existência de uma categoria
    pertencente a outro usuário.

    Args:
        request (Request): A requisição que causou o erro.
        exc (crud.CategoriaInvalidaError): O erro de domínio.

    Returns:
        JSONResponse: Resposta 404 genérica.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Categoria não encontrada."},
    )


@app.exception_handler(SQLAlchemyError)
async def tratar_erro_de_banco(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Impede que detalhes internos do banco vazem para o cliente.

    Mensagens de driver costumam revelar nomes de tabelas, constraints e até
    trechos de SQL — informação valiosa para quem estuda a aplicação.

    Args:
        request (Request): A requisição que causou o erro.
        exc (SQLAlchemyError): A exceção do SQLAlchemy.

    Returns:
        JSONResponse: Resposta 500 genérica.
    """
    logger.exception(
        "Erro de banco de dados",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno ao processar a requisição."},
    )


# --- Validadores de Parâmetros ---


def validar_periodo(data_inicio: date, data_fim: date) -> None:
    """Valida a coerência e a amplitude de um intervalo de datas.

    Args:
        data_inicio (date): Data inicial informada.
        data_fim (date): Data final informada.

    Raises:
        HTTPException: 422 se o intervalo for invertido ou longo demais.
    """
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A data inicial não pode ser posterior à data final.",
        )

    if (data_fim - data_inicio) > timedelta(days=MAXIMO_DIAS_POR_CONSULTA):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "O período consultado excede o limite de "
                f"{MAXIMO_DIAS_POR_CONSULTA} dias."
            ),
        )


# --- ENDPOINTS (Autenticação) ---


@app.post(
    "/token",
    response_model=schemas.Token,
    summary="Login do Usuário",
    dependencies=[Depends(rate_limit_login)],
)
def login_para_obter_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessaoDB,
    contexto: Auditoria,
):
    """Autentica um usuário e retorna um token de acesso JWT.

    A resposta é idêntica para "usuário inexistente" e "senha incorreta", e o
    custo de tempo é equalizado com um hash descartável — sem isso, o tempo de
    resposta revelaria quais nomes de usuário existem.

    Args:
        form_data (OAuth2PasswordRequestForm): Dados do formulário de login.
        db (Session): Sessão do banco de dados.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 401 se as credenciais forem inválidas.

    Returns:
        dict: Token de acesso, tipo e validade em segundos.
    """
    erro_de_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nome de usuário ou senha incorretos",
        headers={"WWW-Authenticate": "Bearer"},
    )

    usuario = crud.get_usuario_por_nome(db, nome_usuario=form_data.username)

    if usuario is None:
        # Equaliza o tempo de resposta com o caso "usuário existe".
        security.consumir_tempo_de_verificacao()
        crud.registrar_tentativa_de_login(
            db, form_data.username, sucesso=False, contexto=contexto
        )
        raise erro_de_credenciais

    if not security.verificar_senha(form_data.password, usuario.senha_hash):
        crud.registrar_tentativa_de_login(
            db,
            form_data.username,
            sucesso=False,
            usuario_id=usuario.id,
            contexto=contexto,
        )
        raise erro_de_credenciais

    # Migra hashes gerados com parâmetros de custo antigos, de forma
    # transparente para o usuário.
    if security.precisa_reidratar_hash(usuario.senha_hash):
        usuario.senha_hash = security.get_hash_da_senha(form_data.password)
        db.commit()

    crud.registrar_tentativa_de_login(
        db, form_data.username, sucesso=True, usuario_id=usuario.id, contexto=contexto
    )

    access_token = security.criar_token_de_acesso(
        nome_usuario=usuario.nome_usuario,
        usuario_id=usuario.id,
        token_version=usuario.token_version,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.post(
    "/usuarios/",
    response_model=schemas.Usuario,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Novo Usuário (Signup)",
    dependencies=[Depends(rate_limit_cadastro)],
)
def criar_novo_usuario(
    usuario: schemas.UsuarioCreate, db: SessaoDB, contexto: Auditoria
):
    """Registra um novo usuário na plataforma.

    A unicidade do nome é garantida pela constraint do banco, e não por uma
    consulta prévia: entre o `SELECT` e o `INSERT` existe uma janela em que duas
    requisições simultâneas passariam pela verificação.

    Args:
        usuario (schemas.UsuarioCreate): Dados para criação do usuário.
        db (Session): Sessão do banco de dados.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 400 se a senha for fraca ou o nome já estiver em uso.

    Returns:
        models.Usuario: O usuário criado.
    """
    problemas = security.validar_forca_da_senha(usuario.senha)
    if problemas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"mensagem": "A senha não atende à política de segurança.",
                    "problemas": problemas},
        )

    try:
        return crud.criar_usuario(db=db, usuario=usuario, contexto=contexto)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já registrado",
        ) from None


@app.get("/", summary="Endpoint Raiz")
def ler_raiz():
    """Retorna uma mensagem de identificação da API.

    Returns:
        dict: Mensagem de boas-vindas.
    """
    return {"message": "Bem-vindo à API de Controle Financeiro!"}


@app.get("/health", summary="Health Check")
def health_check(db: SessaoDB):
    """Verifica se a API e o banco de dados estão operacionais.

    Ao contrário de um health check estático, este endpoint executa uma consulta
    real: um processo que responde mas não alcança o banco não está saudável.

    Args:
        db (Session): Sessão do banco de dados.

    Raises:
        HTTPException: 503 se o banco estiver inacessível.

    Returns:
        dict: Situação da API e de suas dependências.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check falhou: banco de dados inacessível")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço indisponível.",
        ) from None

    return {"status": "ok", "banco_de_dados": "ok"}


# --- ENDPOINTS DE PERFIL DE USUÁRIO ---


@app.get(
    "/usuarios/me", response_model=schemas.Usuario, summary="Ler Perfil do Usuário Logado"
)
def ler_perfil_do_usuario(usuario_atual: UsuarioAutenticado):
    """Retorna as informações do perfil do usuário autenticado.

    Args:
        usuario_atual (models.Usuario): Usuário obtido via token.

    Returns:
        models.Usuario: O objeto usuário.
    """
    return usuario_atual


@app.put(
    "/usuarios/me", response_model=schemas.Usuario, summary="Atualizar Perfil do Usuário"
)
def atualizar_perfil_do_usuario(
    detalhes: schemas.UsuarioUpdate,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Atualiza as informações cadastrais do usuário logado.

    Args:
        detalhes (schemas.UsuarioUpdate): Dados a serem atualizados.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 400 se houver conflito de nome de usuário ou email.

    Returns:
        models.Usuario: O usuário com os dados atualizados.
    """
    try:
        return crud.atualizar_detalhes_usuario(
            db=db, usuario=usuario_atual, detalhes=detalhes, contexto=contexto
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse nome de usuário ou email já está em uso.",
        ) from None


@app.post(
    "/usuarios/mudar-senha",
    response_model=schemas.MensagemDeSucesso,
    summary="Alterar Senha",
)
def mudar_senha(
    payload: schemas.UsuarioChangePassword,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Altera a senha do usuário e revoga todas as sessões ativas.

    Após a troca, o token usado nesta própria requisição também deixa de valer:
    o cliente precisa autenticar novamente. É o comportamento correto quando a
    troca de senha responde a uma suspeita de comprometimento.

    Args:
        payload (schemas.UsuarioChangePassword): Senha atual e nova senha.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 400 se a senha atual estiver incorreta ou a nova for fraca.

    Returns:
        dict: Mensagem de sucesso.
    """
    problemas = security.validar_forca_da_senha(payload.senha_nova)
    if problemas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"mensagem": "A nova senha não atende à política de segurança.",
                    "problemas": problemas},
        )

    sucesso = crud.mudar_senha_usuario(
        db=db, usuario=usuario_atual, payload=payload, contexto=contexto
    )
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha antiga está incorreta.",
        )

    return {
        "message": (
            "Senha atualizada com sucesso. Todas as sessões foram encerradas; "
            "faça login novamente."
        )
    }


@app.post(
    "/usuarios/me/revogar-sessoes",
    response_model=schemas.MensagemDeSucesso,
    summary="Encerrar Todas as Sessões",
)
def revogar_todas_as_sessoes(
    db: SessaoDB, usuario_atual: UsuarioAutenticado, contexto: Auditoria
):
    """Invalida imediatamente todos os tokens de acesso emitidos ao usuário.

    Útil quando o usuário suspeita que um dispositivo foi comprometido, sem
    exigir a troca de senha.

    Args:
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Returns:
        dict: Mensagem de sucesso.
    """
    crud.revogar_sessoes(db=db, usuario=usuario_atual, contexto=contexto)
    return {"message": "Todas as sessões foram encerradas. Faça login novamente."}


# --- ENDPOINTS (Relatórios e Dashboard) ---


@app.get(
    "/dashboard/", response_model=schemas.DashboardData, summary="Ler Dados do Dashboard"
)
def ler_dados_dashboard(
    data_inicio: date,
    data_fim: date,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
):
    """Obtém o resumo financeiro para o dashboard.

    Args:
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        schemas.DashboardData: Dados consolidados do período.
    """
    validar_periodo(data_inicio, data_fim)

    return crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@app.get(
    "/relatorios/tendencia",
    response_model=schemas.DadosDeTendencia,
    summary="Ler Dados do Gráfico de Linha",
)
def ler_dados_de_tendencia(
    data_inicio: date,
    data_fim: date,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    filtro: Annotated[str, Query(pattern="^(daily|weekly|monthly|yearly)$")] = "monthly",
):
    """Obtém dados para gráficos de tendência (evolução temporal).

    Args:
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        filtro (str): Granularidade do agrupamento.

    Returns:
        schemas.DadosDeTendencia: Séries temporais de receitas e despesas.
    """
    validar_periodo(data_inicio, data_fim)

    return crud.get_dados_de_tendencia(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        filtro=filtro,
    )


@app.get(
    "/transacoes/periodo/",
    response_model=list[schemas.Transacao],
    summary="Listar Transações por Período",
)
def ler_transacoes_por_periodo(
    data_inicio: date,
    data_fim: date,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
):
    """Lista as transações do usuário dentro de um intervalo de datas.

    Args:
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        List[schemas.Transacao]: Lista de transações encontradas.
    """
    validar_periodo(data_inicio, data_fim)

    return crud.listar_transacoes_por_periodo(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


# --- ENDPOINTS DE TRANSAÇÃO ---


@app.post(
    "/transacoes/",
    response_model=schemas.DashboardData,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Transação",
)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate,
    data_inicio: date,
    data_fim: date,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Cria uma nova transação e retorna o dashboard atualizado.

    Aceita o cabeçalho `Idempotency-Key`. Se a mesma chave for reenviada — por
    retry automático do cliente ou pela fila de sincronização offline — a
    transação original é devolvida em vez de um lançamento duplicado.

    Args:
        transacao (schemas.TransacaoCreate): Dados da nova transação.
        data_inicio (date): Início do período para recálculo do dashboard.
        data_fim (date): Fim do período para recálculo do dashboard.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.
        idempotency_key (Optional[str]): Chave de idempotência do cliente.

    Raises:
        HTTPException: 404 se a categoria não pertencer ao usuário.

    Returns:
        schemas.DashboardData: Dados atualizados do dashboard.
    """
    validar_periodo(data_inicio, data_fim)

    if idempotency_key is not None and len(idempotency_key) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key excede 64 caracteres.",
        )

    crud.criar_transacao(
        db=db,
        transacao=transacao,
        usuario_id=usuario_atual.id,
        chave_idempotencia=idempotency_key,
        contexto=contexto,
    )

    return crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@app.put(
    "/transacoes/{transacao_id}",
    response_model=schemas.DashboardData,
    summary="Editar Transação",
)
def editar_transacao(
    transacao_id: int,
    transacao: schemas.TransacaoCreate,
    data_inicio: date,
    data_fim: date,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Edita uma transação existente e retorna o dashboard atualizado.

    Args:
        transacao_id (int): ID da transação a ser editada.
        transacao (schemas.TransacaoCreate): Novos dados da transação.
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 404 se a transação não pertencer ao usuário.

    Returns:
        schemas.DashboardData: Dados atualizados do dashboard.
    """
    validar_periodo(data_inicio, data_fim)

    db_transacao = crud.atualizar_transacao(
        db=db,
        transacao_id=transacao_id,
        transacao=transacao,
        usuario_id=usuario_atual.id,
        contexto=contexto,
    )
    if db_transacao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada"
        )

    return crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@app.delete(
    "/transacoes/{transacao_id}",
    response_model=schemas.DashboardData,
    summary="Deletar Transação",
)
def deletar_transacao_e_recalcular(
    transacao_id: int,
    data_inicio: date,
    data_fim: date,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Remove uma transação e retorna o dashboard atualizado.

    Args:
        transacao_id (int): ID da transação a ser removida.
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 404 se a transação não pertencer ao usuário.

    Returns:
        schemas.DashboardData: Dados atualizados do dashboard.
    """
    validar_periodo(data_inicio, data_fim)

    sucesso = crud.deletar_transacao(
        db=db,
        transacao_id=transacao_id,
        usuario_id=usuario_atual.id,
        contexto=contexto,
    )
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada"
        )

    return crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@app.get(
    "/transacoes/",
    response_model=list[schemas.Transacao],
    summary="Listar Últimas Transações (Paginado)",
)
def ler_transacoes(
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    skip: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    # O teto impede que um cliente peça a tabela inteira em uma requisição.
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    """Lista as transações mais recentes do usuário, com paginação.

    Args:
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        skip (int): Quantidade de registros a pular.
        limit (int): Máximo de registros a retornar (teto de 200).

    Returns:
        List[schemas.Transacao]: Lista de transações.
    """
    return crud.listar_transacoes(
        db, usuario_id=usuario_atual.id, skip=skip, limit=limit
    )


# --- ENDPOINTS DE CATEGORIA ---


@app.post(
    "/categorias/",
    response_model=schemas.Categoria,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Categoria",
)
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Cria uma nova categoria pertencente ao usuário autenticado.

    Args:
        categoria (schemas.CategoriaCreate): Dados da nova categoria.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 400 se o usuário já tiver categoria com o mesmo nome.

    Returns:
        schemas.Categoria: A categoria criada.
    """
    try:
        return crud.criar_categoria(
            db=db,
            categoria=categoria,
            usuario_id=usuario_atual.id,
            contexto=contexto,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma categoria com este nome já existe.",
        ) from None


@app.get(
    "/categorias/", response_model=list[schemas.Categoria], summary="Listar Categorias"
)
def ler_categorias(db: SessaoDB, usuario_atual: UsuarioAutenticado):
    """Retorna as categorias do usuário autenticado.

    Args:
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        List[schemas.Categoria]: Lista de categorias do usuário.
    """
    return crud.listar_categorias(db=db, usuario_id=usuario_atual.id)


@app.put(
    "/categorias/{categoria_id}",
    response_model=schemas.Categoria,
    summary="Editar Categoria",
)
def editar_categoria(
    categoria_id: int,
    categoria: schemas.CategoriaUpdate,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Atualiza uma categoria do usuário autenticado.

    Args:
        categoria_id (int): ID da categoria.
        categoria (schemas.CategoriaUpdate): Dados a serem atualizados.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 400 em conflito de nome, 404 se não for do usuário.

    Returns:
        schemas.Categoria: A categoria atualizada.
    """
    try:
        db_categoria = crud.atualizar_categoria(
            db=db,
            categoria_id=categoria_id,
            categoria_update=categoria,
            usuario_id=usuario_atual.id,
            contexto=contexto,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma categoria com este nome já existe.",
        ) from None

    if db_categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )

    return db_categoria


@app.delete(
    "/categorias/{categoria_id}",
    response_model=schemas.MensagemDeSucesso,
    summary="Deletar Categoria",
)
def deletar_categoria_endpoint(
    categoria_id: int,
    db: SessaoDB,
    usuario_atual: UsuarioAutenticado,
    contexto: Auditoria,
):
    """Remove uma categoria do usuário autenticado.

    A remoção é recusada se houver transações classificadas na categoria: apagar
    a categoria destruiria a classificação contábil de lançamentos históricos.

    Args:
        categoria_id (int): ID da categoria.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.
        contexto (crud.ContextoDeAuditoria): Metadados da requisição.

    Raises:
        HTTPException: 404 se não for do usuário, 400 se estiver em uso.

    Returns:
        dict: Mensagem de sucesso.
    """
    # Verificação explícita antes de tentar apagar: produz uma mensagem clara
    # em vez de depender do erro de constraint do banco.
    if crud.categoria_esta_em_uso(db, categoria_id, usuario_atual.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível excluir: esta categoria já está sendo usada "
                "por transações."
            ),
        )

    try:
        sucesso = crud.deletar_categoria(
            db=db,
            categoria_id=categoria_id,
            usuario_id=usuario_atual.id,
            contexto=contexto,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível excluir: esta categoria já está sendo usada "
                "por transações."
            ),
        ) from None

    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )

    return {"message": "Categoria deletada com sucesso."}
