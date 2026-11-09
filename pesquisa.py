
from banco import conectar


def pesquisar_arquivos(termo, limite=30, pagina=1):
    """
    Pesquisa arquivos pelo nome.

    termo: texto ou número procurado.
    limite: quantidade máxima de resultados.
    pagina: página dos resultados.
    """

    termo = str(termo).strip()

    if not termo:
        return {
            "total": 0,
            "pagina": pagina,
            "limite": limite,
            "resultados": []
        }

    if limite < 1:
        limite = 30

    if limite > 100:
        limite = 100

    if pagina < 1:
        pagina = 1

    deslocamento = (pagina - 1) * limite

    # Escapa caracteres especiais do LIKE
    termo = (
        termo
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    parametro = f"%{termo}%"

    with conectar() as conn:

        total = conn.execute("""
            SELECT COUNT(*)
            FROM arquivos
            WHERE nome LIKE ? ESCAPE '\\'
        """, (parametro,)).fetchone()[0]

        registros = conn.execute("""
            SELECT
                id,
                nome,
                caminho,
                extensao,
                tamanho_bytes,
                modificado_em
            FROM arquivos
            WHERE nome LIKE ? ESCAPE '\\'
            ORDER BY nome COLLATE NOCASE
            LIMIT ? OFFSET ?
        """, (
            parametro,
            limite,
            deslocamento
        )).fetchall()

    resultados = []

    for registro in registros:
        resultados.append({
            "id": registro[0],
            "nome": registro[1],
            "caminho": registro[2],
            "extensao": registro[3],
            "tamanho_bytes": registro[4],
            "modificado_em": registro[5]
        })

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "resultados": resultados
    }
