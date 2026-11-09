"""
Indexador inicial do Catálogo de Notas Fiscais.

Percorre a origem recursivamente e grava metadados no SQLite.
Não abre o conteúdo dos documentos e não move, renomeia ou exclui originais.
Nesta etapa, também não remove registros antigos do catálogo.
"""
import os
import sys
import time
from pathlib import Path

from banco import inicializar_banco, conectar, CAMINHO_BANCO
from configuracao import (
    PASTA_ORIGEM, EXTENSOES_PERMITIDAS, PASTAS_IGNORADAS,
    PREFIXOS_IGNORADOS, EXTENSOES_IGNORADAS,
)


def arquivo_deve_ser_indexado(caminho: Path) -> bool:
    nome = caminho.name
    extensao = caminho.suffix.lower()

    if nome.startswith(PREFIXOS_IGNORADOS):
        return False
    if extensao in EXTENSOES_IGNORADAS:
        return False
    if EXTENSOES_PERMITIDAS is not None:
        permitidas = {ext.lower() for ext in EXTENSOES_PERMITIDAS}
        if extensao not in permitidas:
            return False
    return True


def percorrer_arquivos(raiz: Path):
    """Percorre diretórios sem seguir links simbólicos; avisa sobre falhas."""
    pilha = [raiz]

    while pilha:
        pasta_atual = pilha.pop()
        try:
            with os.scandir(pasta_atual) as itens:
                for item in itens:
                    try:
                        if item.is_dir(follow_symlinks=False):
                            if item.name.lower() not in PASTAS_IGNORADAS:
                                pilha.append(Path(item.path))
                        elif item.is_file(follow_symlinks=False):
                            caminho = Path(item.path)
                            if arquivo_deve_ser_indexado(caminho):
                                yield caminho
                    except (PermissionError, OSError) as erro:
                        print(f"[AVISO] Não foi possível acessar {item.path}: {erro}")
        except (PermissionError, OSError) as erro:
            print(f"[AVISO] Não foi possível listar {pasta_atual}: {erro}")


def indexar() -> int:
    inicio = time.perf_counter()

    if not PASTA_ORIGEM.exists():
        print("[ERRO] Pasta de origem não encontrada ou inacessível.")
        print(f"Caminho: {PASTA_ORIGEM}")
        print("Verifique rede e permissões de leitura.")
        return 1
    if not PASTA_ORIGEM.is_dir():
        print("[ERRO] O caminho configurado não é uma pasta.")
        return 1

    inicializar_banco()
    encontrados = cadastrados = atualizados = inalterados = falhas = 0

    print("Iniciando catalogação...")
    print(f"Origem: {PASTA_ORIGEM}")
    print(f"Banco:  {CAMINHO_BANCO}")
    print("-" * 60)

    with conectar() as conexao:
        for caminho in percorrer_arquivos(PASTA_ORIGEM):
            encontrados += 1
            try:
                dados = caminho.stat()
                nome = caminho.name
                caminho_completo = os.path.normpath(str(caminho))
                extensao = caminho.suffix.lower() or None
                tamanho = dados.st_size
                modificado_em = dados.st_mtime
                modificado_ns = getattr(
                    dados, "st_mtime_ns", int(dados.st_mtime * 1_000_000_000)
                )

                existente = conexao.execute(
                    """SELECT nome, extensao, tamanho_bytes, modificado_ns
                       FROM arquivos WHERE caminho = ?""",
                    (caminho_completo,),
                ).fetchone()

                if existente is None:
                    conexao.execute(
                        """INSERT INTO arquivos
                           (nome, caminho, extensao, tamanho_bytes,
                            modificado_em, modificado_ns)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (nome, caminho_completo, extensao, tamanho,
                         modificado_em, modificado_ns),
                    )
                    cadastrados += 1
                elif (
                    existente["nome"] != nome
                    or existente["extensao"] != extensao
                    or existente["tamanho_bytes"] != tamanho
                    or existente["modificado_ns"] != modificado_ns
                ):
                    conexao.execute(
                        """UPDATE arquivos
                           SET nome = ?, extensao = ?, tamanho_bytes = ?,
                               modificado_em = ?, modificado_ns = ?
                           WHERE caminho = ?""",
                        (nome, extensao, tamanho, modificado_em,
                         modificado_ns, caminho_completo),
                    )
                    atualizados += 1
                else:
                    inalterados += 1

                if encontrados % 100 == 0:
                    print(
                        f"Verificados: {encontrados} | Novos: {cadastrados} | "
                        f"Atualizados: {atualizados}"
                    )
            except (PermissionError, OSError) as erro:
                falhas += 1
                print(f"[AVISO] Falha ao consultar {caminho}: {erro}")

    duracao = time.perf_counter() - inicio
    print("-" * 60)
    print("CATALOGAÇÃO CONCLUÍDA")
    print(f"Arquivos encontrados: {encontrados}")
    print(f"Novos cadastrados:   {cadastrados}")
    print(f"Atualizados:         {atualizados}")
    print(f"Sem alterações:      {inalterados}")
    print(f"Falhas de leitura:   {falhas}")
    print(f"Tempo:               {duracao:.2f} segundos")
    print(f"Banco:               {CAMINHO_BANCO}")
    print("Os documentos originais não foram alterados.")
    return 0


if __name__ == "__main__":
    sys.exit(indexar())
