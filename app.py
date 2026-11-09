
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse

from pesquisa import pesquisar_arquivos
from banco import conectar
from configuracao import PASTA_ORIGEM


app = FastAPI(
    title="Catálogo de Notas Fiscais",
    description="Sistema de pesquisa de notas fiscais",
    version="1.0.0"
)


ARQUIVO_HTML = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def inicio():
    if not ARQUIVO_HTML.exists():
        raise HTTPException(
            status_code=500,
            detail="Arquivo da interface não encontrado."
        )

    return FileResponse(ARQUIVO_HTML)


@app.get("/pesquisar")
def pesquisar(
    q: str = Query(..., min_length=1, max_length=200),
    pagina: int = Query(1, ge=1),
    limite: int = Query(30, ge=1, le=100)
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


@app.get("/arquivo/{arquivo_id}")
def baixar_arquivo(arquivo_id: int):

    # Busca o caminho do arquivo no banco
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

    nome = registro[0]
    caminho = Path(registro[1])

    try:
        raiz = Path(PASTA_ORIGEM).resolve()
        arquivo = caminho.resolve()

        # Verifica se o arquivo pertence à pasta autorizada
        arquivo.relative_to(raiz)

    except (ValueError, OSError):
        raise HTTPException(
            status_code=403,
            detail="Acesso ao arquivo não autorizado."
        )

    # Confirma que o arquivo ainda existe
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
