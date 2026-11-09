"""Teste simples da estrutura criada na Etapa 1."""

from banco import inicializar_banco, obter_resumo, conectar


def testar():
    inicializar_banco()

    # Confere se a tabela existe.
    with conectar() as conexao:
        tabela = conexao.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'arquivos'
        """).fetchone()

        indices = conexao.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_arquivos_%'
            ORDER BY name
        """).fetchall()

    assert tabela is not None, "A tabela 'arquivos' não foi criada."
    assert len(indices) >= 3, "Os índices esperados não foram criados."

    print("TESTE CONCLUÍDO: tabela e índices encontrados.")
    print(obter_resumo())


if __name__ == "__main__":
    testar()
