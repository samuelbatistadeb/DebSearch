
"""
Banco de dados do DebDocs
Gerenciamento do catálogo e dos usuários.
"""

from pathlib import Path
import sqlite3


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
    """Cria as estruturas necessárias, se ainda não existirem."""

    with conectar() as conexao:

        conexao.execute("PRAGMA journal_mode = WAL")

        # Tabela de arquivos
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

        # Índices dos arquivos
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

        # Tabela de usuários
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL COLLATE NOCASE UNIQUE,
                senha_hash TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                administrador INTEGER NOT NULL DEFAULT 0,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    return CAMINHO_BANCO


def obter_resumo():
    """Retorna informações do catálogo e do banco."""

    with conectar() as conexao:
        quantidade = conexao.execute(
            "SELECT COUNT(*) FROM arquivos"
        ).fetchone()[0]

        quantidade_usuarios = conexao.execute(
            "SELECT COUNT(*) FROM usuarios"
        ).fetchone()[0]

    tamanho = (
        CAMINHO_BANCO.stat().st_size
        if CAMINHO_BANCO.exists()
        else 0
    )

    return {
        "caminho": str(CAMINHO_BANCO),
        "quantidade_arquivos": quantidade,
        "quantidade_usuarios": quantidade_usuarios,
        "tamanho_bytes": tamanho,
    }


if __name__ == "__main__":

    caminho = inicializar_banco()
    resumo = obter_resumo()

    print("Banco de dados inicializado com sucesso.")
    print(f"Local: {caminho}")
    print(f"Arquivos cadastrados: {resumo['quantidade_arquivos']}")
    print(f"Usuários cadastrados: {resumo['quantidade_usuarios']}")
    print(f"Tamanho atual: {resumo['tamanho_bytes']} bytes")
