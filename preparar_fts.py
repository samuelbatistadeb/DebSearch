
from banco import conectar


def preparar_indice():
    with conectar() as conn:

        indice_existe = conn.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'arquivos_fts'
        """).fetchone()

        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS arquivos_fts
            USING fts5(
                nome,
                content='arquivos',
                content_rowid='id',
                tokenize='trigram'
            )
        """)

        # Cadastro de novos arquivos
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS arquivos_ai
            AFTER INSERT ON arquivos
            BEGIN
                INSERT INTO arquivos_fts(rowid, nome)
                VALUES (new.id, new.nome);
            END;
        """)

        # Atualização somente quando o nome realmente mudar
        conn.execute("""
            DROP TRIGGER IF EXISTS arquivos_au
        """)

        conn.execute("""
            CREATE TRIGGER arquivos_au
            AFTER UPDATE OF nome ON arquivos
            WHEN old.nome IS NOT new.nome
            BEGIN
                INSERT INTO arquivos_fts(
                    arquivos_fts,
                    rowid,
                    nome
                )
                VALUES (
                    'delete',
                    old.id,
                    old.nome
                );

                INSERT INTO arquivos_fts(rowid, nome)
                VALUES (new.id, new.nome);
            END;
        """)

        # Exclusão de arquivos
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS arquivos_ad
            AFTER DELETE ON arquivos
            BEGIN
                INSERT INTO arquivos_fts(
                    arquivos_fts,
                    rowid,
                    nome
                )
                VALUES (
                    'delete',
                    old.id,
                    old.nome
                );
            END;
        """)

        # Reconstrói o índice somente se ele ainda não existia
        if indice_existe is None:
            print("Criando índice inicial...")

            conn.execute("""
                INSERT INTO arquivos_fts(arquivos_fts)
                VALUES ('rebuild')
            """)

        total = conn.execute("""
            SELECT COUNT(*) FROM arquivos
        """).fetchone()[0]

    print("\nÍNDICE FTS5 PREPARADO")
    print(f"Arquivos cadastrados: {total:,}".replace(",", "."))
    print("Gatilhos de sincronização: habilitados")


if __name__ == "__main__":
    preparar_indice()
