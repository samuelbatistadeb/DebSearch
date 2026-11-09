
from banco import conectar, obter_resumo

print("\n===== RESUMO DO CATÁLOGO =====")

print(obter_resumo())

with conectar() as conn:
    registros = conn.execute("""
        SELECT
            nome,
            caminho,
            tamanho_bytes,
            extensao
        FROM arquivos
        ORDER BY nome
    """).fetchall()

print("\n===== ARQUIVOS CADASTRADOS =====")

for registro in registros:
    print(f"\nNome: {registro[0]}")
    print(f"Caminho: {registro[1]}")
    print(f"Tamanho: {registro[2]} bytes")
    print(f"Extensão: {registro[3]}")

print(f"\nTotal de registros: {len(registros)}")
