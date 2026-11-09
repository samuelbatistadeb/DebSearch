
from pesquisa import pesquisar_arquivos


print("===== PESQUISA DE NOTAS FISCAIS =====")

while True:

    termo = input("\nDigite o nome ou número da nota (ou SAIR): ")

    if termo.strip().upper() == "SAIR":
        break

    resultado = pesquisar_arquivos(
        termo=termo,
        limite=30,
        pagina=1
    )

    print("\nResultados encontrados:", resultado["total"])

    if not resultado["resultados"]:
        print("Nenhum arquivo encontrado.")
        continue

    for arquivo in resultado["resultados"]:

        print("\n--------------------------------")

        print("Nome:", arquivo["nome"])
        print("Caminho:", arquivo["caminho"])
        print("Extensão:", arquivo["extensao"])
        print("Tamanho:", arquivo["tamanho_bytes"], "bytes")
