
"""
Banco de dados do DebSearch
Gerenciamento do catálogo, usuários e segurança de autenticação.
"""

from pathlib import Path
import sqlite3


PASTA_PROJETO = Path(__file__).resolve().parent
PASTA_DATABASE = PASTA_PROJETO / "database"
CAMINHO_BANCO = PASTA_DATABASE / "catalogo.db"


def conectar():
    """Abre uma conexão com o banco SQLite."""

    PASTA_DATABASE.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(
        CAMINHO_BANCO,
        timeout=30
    )

    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


def inicializar_banco():
    """Cria as estruturas necessárias, se ainda não existirem."""

    with conectar() as conexao:

        conexao.execute("PRAGMA journal_mode = WAL")

        # =====================================
        # TABELA DE ARQUIVOS
        # =====================================

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

        # =====================================
        # TABELA DE USUÁRIOS
        # =====================================

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

        # =====================================
        # CONTROLE DE TENTATIVAS DE LOGIN
        # =====================================

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS tentativas_login (
                ip TEXT NOT NULL,
                usuario_normalizado TEXT NOT NULL,

                falhas INTEGER NOT NULL DEFAULT 0,

                inicio_janela REAL,
                bloqueado_ate REAL,

                nivel_bloqueio INTEGER NOT NULL DEFAULT 0,

                atualizado_em REAL NOT NULL,

                PRIMARY KEY (
                    ip,
                    usuario_normalizado
                )
            )
        """)

        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_tentativas_login_atualizado
            ON tentativas_login(atualizado_em)
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
