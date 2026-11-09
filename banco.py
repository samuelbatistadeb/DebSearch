"""
Banco de dados do Catálogo de Notas Fiscais
Etapa 1: criação e validação da estrutura SQLite.

Este módulo NÃO percorre nem altera a pasta de documentos.
"""

from pathlib import Path
import sqlite3

# Por enquanto, o banco fica dentro da pasta do projeto.
# Na implantação no servidor, podemos alterar este caminho pela configuração.
PASTA_PROJETO = Path(__file__).resolve().parent
PASTA_DATABASE = PASTA_PROJETO / "database"
CAMINHO_BANCO = PASTA_DATABASE / "catalogo.db"


def conectar():
    """Abre uma conexão com o banco SQLite."""
    PASTA_DATABASE.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=30)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_banco():
    """Cria o banco, a tabela de arquivos e os índices, se ainda não existirem."""
    with conectar() as conexao:
        # WAL melhora a convivência entre consultas e atualizações.
        # O banco deve permanecer no disco local do servidor, não em uma pasta SMB.
        conexao.execute("PRAGMA journal_mode = WAL")

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS arquivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                caminho TEXT NOT NULL COLLATE NOCASE UNIQUE,
                extensao TEXT,
                tamanho_bytes INTEGER NOT NULL DEFAULT 0,
                modificado_em REAL,
                modificado_ns INTEGER,
                cadastrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices úteis para filtros e ordenação.
        # A pesquisa por trecho do nome será otimizada em uma etapa posterior.
        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_arquivos_nome
            ON arquivos(nome)
        """)
        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_arquivos_extensao
            ON arquivos(extensao)
        """)
        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_arquivos_modificado_ns
            ON arquivos(modificado_ns)
        """)

    return CAMINHO_BANCO


def obter_resumo():
    """Retorna quantidade de registros e tamanho do banco."""
    with conectar() as conexao:
        quantidade = conexao.execute(
            "SELECT COUNT(*) FROM arquivos"
        ).fetchone()[0]

    tamanho = CAMINHO_BANCO.stat().st_size if CAMINHO_BANCO.exists() else 0

    return {
        "caminho": str(CAMINHO_BANCO),
        "quantidade_arquivos": quantidade,
        "tamanho_bytes": tamanho,
    }


if __name__ == "__main__":
    caminho = inicializar_banco()
    resumo = obter_resumo()

    print("Banco de dados inicializado com sucesso.")
    print(f"Local: {caminho}")
    print(f"Registros cadastrados: {resumo['quantidade_arquivos']}")
    print(f"Tamanho atual: {resumo['tamanho_bytes']} bytes")
