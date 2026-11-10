
from pathlib import Path

from fastapi import (
    FastAPI,
    Query,
    HTTPException,
    Request,
    Depends,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from pesquisa import pesquisar_arquivos
from banco import conectar
from configuracao import (
    PASTA_ORIGEM,
    DEBDOCS_SECRET_KEY,
    TEMPO_SESSAO_SEGUNDOS,
    COOKIE_SEGURO
)
from usuarios import autenticar_usuario, obter_usuario


# Verifica se a chave de sessão está configurada.
if not DEBDOCS_SECRET_KEY:
    raise RuntimeError(
        "A variável DEBDOCS_SECRET_KEY não foi configurada."
    )


app = FastAPI(
    title="DebDocs - Catálogo de Notas Fiscais",
    description="Sistema de pesquisa de notas fiscais",
    version="1.1.0"
)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)
# Configuração das sessões.
app.add_middleware(
    SessionMiddleware,
    secret_key=DEBDOCS_SECRET_KEY,
    max_age=TEMPO_SESSAO_SEGUNDOS,
    same_site="lax",
    https_only=COOKIE_SEGURO
)


ARQUIVO_HTML = Path(__file__).parent / "static" / "index.html"


# Dados recebidos no login.
class DadosLogin(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=256)


# Verifica se existe uma sessão válida.
def usuario_autenticado(request: Request):
    usuario_id = request.session.get("usuario_id")

    if usuario_id is None:
        raise HTTPException(
            status_code=401,
            detail="Autenticação necessária."
        )

    usuario = obter_usuario(usuario_id)

    if usuario is None:
        request.session.clear()

        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou usuário desativado."
        )

    return usuario


# Login
@app.post("/login")
def login(dados: DadosLogin, request: Request):

    usuario = autenticar_usuario(
        dados.usuario,
        dados.senha
    )

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha inválidos."
        )

    # Limpa qualquer sessão anterior.
    request.session.clear()

    # Armazena somente o identificador do usuário.
    request.session["usuario_id"] = usuario["id"]

    return {
        "mensagem": "Login realizado com sucesso.",
        "usuario": usuario
    }


# Consulta a sessão atual.
@app.get("/me")
def consultar_sessao(request: Request):

    try:
        usuario = usuario_autenticado(request)

        return {
            "autenticado": True,
            "usuario": usuario
        }

    except HTTPException as erro:
        if erro.status_code == 401:
            return {
                "autenticado": False,
                "usuario": None
            }

        raise


# Logout
@app.post("/logout")
def logout(request: Request):

    request.session.clear()

    return {
        "mensagem": "Sessão encerrada com sucesso."
    }


# Interface
@app.get("/", include_in_schema=False)
def inicio():

    if not ARQUIVO_HTML.exists():
        raise HTTPException(
            status_code=500,
            detail="Arquivo da interface não encontrado."
        )

    return FileResponse(ARQUIVO_HTML)


# Pesquisa protegida.
@app.get("/pesquisar")
def pesquisar(
    q: str = Query(..., min_length=1, max_length=200),
    pagina: int = Query(1, ge=1),
    limite: int = Query(30, ge=1, le=100),
    usuario: dict = Depends(usuario_autenticado)
):
    try:
        return pesquisar_arquivos(
            termo=q,
            pagina=pagina,
            limite=limite
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao realizar a pesquisa."
        )


# Download protegido.
@app.get("/arquivo/{arquivo_id}")
def baixar_arquivo(
    arquivo_id: int,
    usuario: dict = Depends(usuario_autenticado)
):

    # Busca o caminho do arquivo no banco.
    with conectar() as conn:
        registro = conn.execute(
            """
            SELECT nome, caminho
            FROM arquivos
            WHERE id = ?
            """,
            (arquivo_id,)
        ).fetchone()

    if registro is None:
        raise HTTPException(
            status_code=404,
            detail="Arquivo não encontrado no catálogo."
        )

    nome = registro["nome"]
    caminho = Path(registro["caminho"])

    try:
        raiz = Path(PASTA_ORIGEM).resolve()
        arquivo = caminho.resolve()

        # Verifica se o arquivo pertence à pasta autorizada.
        arquivo.relative_to(raiz)

    except (ValueError, OSError):
        raise HTTPException(
            status_code=403,
            detail="Acesso ao arquivo não autorizado."
        )

    # Confirma que o arquivo ainda existe.
    if not arquivo.is_file():
        raise HTTPException(
            status_code=404,
            detail="O arquivo não existe mais na pasta de origem."
        )

    return FileResponse(
        path=arquivo,
        filename=nome,
        content_disposition_type="attachment"
    )
