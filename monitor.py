
"""
Monitor incremental do DebSearch.

Acompanha alterações na pasta de origem e mantém o catálogo SQLite atualizado.

- Cadastra arquivos novos.
- Atualiza arquivos modificados.
- Remove registros de arquivos excluídos.
- Trata movimentações e renomeações.
- Respeita os mesmos filtros do indexador.py.
- Faz reconciliações periódicas para recuperar eventos perdidos.
- Só remove registros antigos quando a varredura termina sem erros.
"""

import os
import time
import queue
import logging
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from configuracao import (
    PASTA_ORIGEM,
    EXTENSOES_PERMITIDAS,
    PASTAS_IGNORADAS,
    PREFIXOS_IGNORADOS,
    EXTENSOES_IGNORADAS,
)

from banco import conectar, inicializar_banco
from preparar_fts import preparar_indice


# =========================================================
# CONFIGURAÇÕES DO MONITOR
# =========================================================

# Reconciliação completa a cada 6 horas.
INTERVALO_RECONCILIACAO = 6 * 60 * 60

# Agrupamento de eventos recebidos em sequência.
TEMPO_AGRUPAMENTO = 1

# Tempo máximo para aguardar um arquivo estabilizar.
TENTATIVAS_ESTABILIDADE = 15
INTERVALO_ESTABILIDADE = 1


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


# =========================================================
# CONTROLE INTERNO
# =========================================================

fila_eventos = queue.Queue()
bloqueio_catalogo = threading.RLock()

RAIZ_ORIGEM = os.path.normpath(
    os.path.abspath(str(PASTA_ORIGEM))
)

RAIZ_CHAVE = os.path.normcase(RAIZ_ORIGEM)


# =========================================================
# NORMALIZAÇÃO DE CAMINHOS
# =========================================================

def normalizar_caminho(caminho):
    """
    Padroniza o caminho da mesma maneira que o indexador.
    """

    return os.path.normpath(
        os.path.abspath(os.fspath(caminho))
    )


def chave_caminho(caminho):
    """
    Cria uma chave para comparações sem diferença de
    maiúsculas/minúsculas no Windows.
    """

    return os.path.normcase(
        normalizar_caminho(caminho)
    )


def esta_dentro_da_origem(caminho):
    """
    Verifica se um caminho pertence à pasta monitorada.
    """

    caminho = chave_caminho(caminho)

    try:
        return os.path.commonpath(
            [RAIZ_CHAVE, caminho]
        ) == RAIZ_CHAVE

    except ValueError:
        return False


# =========================================================
# FILTROS DE ARQUIVOS E PASTAS
# =========================================================

def caminho_ignorado(caminho, eh_diretorio=False):
    """
    Aplica os mesmos filtros definidos no configuracao.py
    e utilizados pelo indexador.py.
    """

    caminho = normalizar_caminho(caminho)

    if not esta_dentro_da_origem(caminho):
        return True

    try:
        relativo = os.path.relpath(
            caminho,
            RAIZ_ORIGEM
        )

    except ValueError:
        return True

    partes = relativo.split(os.sep)

    # Verifica pastas ignoradas.
    pastas = partes if eh_diretorio else partes[:-1]

    for nome_pasta in pastas:
        if nome_pasta.lower() in PASTAS_IGNORADAS:
            return True

    # Diretórios não precisam passar pelos filtros de extensão.
    if eh_diretorio:
        return False

    nome = os.path.basename(caminho)
    extensao = os.path.splitext(nome)[1].lower()

    if nome.startswith(PREFIXOS_IGNORADOS):
        return True

    if extensao in EXTENSOES_IGNORADAS:
        return True

    if EXTENSOES_PERMITIDAS is not None:
        permitidas = {
            ext.lower()
            for ext in EXTENSOES_PERMITIDAS
        }

        if extensao not in permitidas:
            return True

    return False


# =========================================================
# ESTABILIDADE DOS ARQUIVOS
# =========================================================

def aguardar_arquivo_estavel(
    caminho,
    tentativas=TENTATIVAS_ESTABILIDADE,
    intervalo=INTERVALO_ESTABILIDADE
):
    """
    Aguarda tamanho e data de modificação permanecerem
    estáveis antes de cadastrar o arquivo.
    """

    estado_anterior = None
    repeticoes = 0

    for _ in range(tentativas):

        try:
            if not os.path.isfile(caminho):
                return False

            estat = os.stat(caminho)

            estado_atual = (
                estat.st_size,
                estat.st_mtime_ns
            )

            if estado_atual == estado_anterior:
                repeticoes += 1

            else:
                repeticoes = 0

            if repeticoes >= 2:
                return True

            estado_anterior = estado_atual

        except OSError:
            repeticoes = 0

        time.sleep(intervalo)

    return False


# =========================================================
# CADASTRO E ATUALIZAÇÃO
# =========================================================

def cadastrar_ou_atualizar(caminho):

    caminho = normalizar_caminho(caminho)

    if caminho_ignorado(caminho):
        return

    if not aguardar_arquivo_estavel(caminho):

        logging.warning(
            "Arquivo não estabilizou ou não está acessível: %s",
            caminho
        )

        return

    try:
        nome = os.path.basename(caminho)
        extensao = os.path.splitext(nome)[1].lower() or None

        estat = os.stat(caminho)

        with conectar() as conn:

            conn.execute(
                """
                INSERT INTO arquivos (
                    nome,
                    caminho,
                    extensao,
                    tamanho_bytes,
                    modificado_em,
                    modificado_ns
                )
                VALUES (?, ?, ?, ?, ?, ?)

                ON CONFLICT(caminho)
                DO UPDATE SET
                    nome = excluded.nome,
                    extensao = excluded.extensao,
                    tamanho_bytes = excluded.tamanho_bytes,
                    modificado_em = excluded.modificado_em,
                    modificado_ns = excluded.modificado_ns

                WHERE
                    arquivos.nome IS NOT excluded.nome
                    OR arquivos.extensao IS NOT excluded.extensao
                    OR arquivos.tamanho_bytes IS NOT excluded.tamanho_bytes
                    OR arquivos.modificado_em IS NOT excluded.modificado_em
                    OR arquivos.modificado_ns IS NOT excluded.modificado_ns
                """,
                (
                    nome,
                    caminho,
                    extensao,
                    estat.st_size,
                    estat.st_mtime,
                    estat.st_mtime_ns
                )
            )

        logging.debug(
            "Arquivo cadastrado/verificado: %s",
            caminho
        )

    except (OSError, Exception):

        logging.exception(
            "Erro ao cadastrar ou atualizar: %s",
            caminho
        )


# =========================================================
# REMOÇÃO DE ARQUIVOS E PASTAS
# =========================================================

def remover_arquivo(caminho):

    caminho = normalizar_caminho(caminho)

    if not esta_dentro_da_origem(caminho):
        return

    try:
        with conectar() as conn:

            cursor = conn.execute(
                """
                DELETE FROM arquivos
                WHERE caminho = ? COLLATE NOCASE
                """,
                (caminho,)
            )

        if cursor.rowcount:
            logging.info(
                "Registro removido: %s",
                caminho
            )

    except Exception:

        logging.exception(
            "Erro ao remover registro: %s",
            caminho
        )


def remover_pasta(caminho):

    caminho = normalizar_caminho(caminho)

    if not esta_dentro_da_origem(caminho):
        return

    # Nunca permitir que um evento remova toda a origem.
    if chave_caminho(caminho) == RAIZ_CHAVE:
        logging.warning(
            "Tentativa de remover a pasta raiz ignorada."
        )
        return

    prefixo = caminho + os.sep

    try:
        with conectar() as conn:

            cursor = conn.execute(
                """
                DELETE FROM arquivos
                WHERE substr(caminho, 1, ?) COLLATE NOCASE = ?
                """,
                (len(prefixo), prefixo)
            )

        logging.info(
            "Registros removidos da pasta %s: %s",
            caminho,
            cursor.rowcount
        )

    except Exception:

        logging.exception(
            "Erro ao remover registros da pasta: %s",
            caminho
        )


# =========================================================
# INDEXAÇÃO DE UMA PASTA
# =========================================================

def indexar_pasta(caminho):

    caminho = normalizar_caminho(caminho)

    if not esta_dentro_da_origem(caminho):
        return

    if caminho_ignorado(caminho, eh_diretorio=True):
        return

    if not os.path.isdir(caminho):
        return

    logging.info(
        "Indexando pasta adicionada: %s",
        caminho
    )

    def registrar_erro(erro):
        logging.error(
            "Erro ao percorrer pasta %s: %s",
            caminho,
            erro
        )

    for raiz, diretorios, arquivos in os.walk(
        caminho,
        onerror=registrar_erro
    ):

        # Remove pastas ignoradas antes de percorrê-las.
        diretorios[:] = [
            nome
            for nome in diretorios
            if nome.lower() not in PASTAS_IGNORADAS
        ]

        for nome in arquivos:

            arquivo = os.path.join(
                raiz,
                nome
            )

            if caminho_ignorado(arquivo):
                continue

            cadastrar_ou_atualizar(arquivo)


# =========================================================
# PROCESSAMENTO DOS EVENTOS
# =========================================================

def _processar_eventos(eventos):

    acoes_arquivos = {}
    acoes_pastas = {}

    for tipo, origem, destino, eh_diretorio in eventos:

        origem = normalizar_caminho(origem)

        if eh_diretorio:

            if tipo == "movido":

                destino = normalizar_caminho(destino)

                acoes_pastas[
                    ("movido", chave_caminho(origem), chave_caminho(destino))
                ] = (tipo, origem, destino)

            else:

                acoes_pastas[
                    (tipo, chave_caminho(origem))
                ] = (tipo, origem, destino)

            continue

        if tipo == "movido":

            destino = normalizar_caminho(destino)

            if esta_dentro_da_origem(origem):
                acoes_arquivos[chave_caminho(origem)] = (
                    "remover",
                    origem
                )

            if esta_dentro_da_origem(destino):
                acoes_arquivos[chave_caminho(destino)] = (
                    "atualizar",
                    destino
                )

        elif tipo == "excluido":

            if esta_dentro_da_origem(origem):
                acoes_arquivos[chave_caminho(origem)] = (
                    "remover",
                    origem
                )

        else:

            if esta_dentro_da_origem(origem):
                acoes_arquivos[chave_caminho(origem)] = (
                    "atualizar",
                    origem
                )

    # -----------------------------------------------------
    # Processa pastas
    # -----------------------------------------------------

    for tipo, origem, destino in acoes_pastas.values():

        if tipo == "criado":

            if not caminho_ignorado(
                origem,
                eh_diretorio=True
            ):
                indexar_pasta(origem)

        elif tipo == "excluido":

            if not caminho_ignorado(
                origem,
                eh_diretorio=True
            ):
                remover_pasta(origem)

        elif tipo == "movido":

            if esta_dentro_da_origem(origem):

                if not caminho_ignorado(
                    origem,
                    eh_diretorio=True
                ):
                    remover_pasta(origem)

            if esta_dentro_da_origem(destino):

                if not caminho_ignorado(
                    destino,
                    eh_diretorio=True
                ):
                    indexar_pasta(destino)

    # -----------------------------------------------------
    # Processa arquivos
    # -----------------------------------------------------

    for acao, caminho in acoes_arquivos.values():

        if acao == "remover":

            remover_arquivo(caminho)

        elif acao == "atualizar":

            cadastrar_ou_atualizar(caminho)


def processar_eventos(eventos):

    with bloqueio_catalogo:
        _processar_eventos(eventos)


# =========================================================
# TRABALHADOR DA FILA
# =========================================================

def trabalhador_eventos():

    logging.info("Fila de eventos iniciada.")

    while True:

        primeiro = fila_eventos.get()

        if primeiro is None:
            break

        eventos = [primeiro]

        time.sleep(TEMPO_AGRUPAMENTO)

        while True:

            try:
                evento = fila_eventos.get_nowait()

                if evento is None:
                    logging.warning(
                        "Encerramento solicitado durante o agrupamento."
                    )
                    return

                eventos.append(evento)

            except queue.Empty:
                break

        try:
            processar_eventos(eventos)

        except Exception:

            logging.exception(
                "Erro ao processar eventos da fila."
            )


# =========================================================
# MANIPULADOR DO WATCHDOG
# =========================================================

class MonitorDeArquivos(FileSystemEventHandler):

    def on_created(self, event):

        fila_eventos.put((
            "criado",
            event.src_path,
            None,
            event.is_directory
        ))

    def on_modified(self, event):

        if not event.is_directory:

            fila_eventos.put((
                "alterado",
                event.src_path,
                None,
                False
            ))

    def on_deleted(self, event):

        fila_eventos.put((
            "excluido",
            event.src_path,
            None,
            event.is_directory
        ))

    def on_moved(self, event):

        fila_eventos.put((
            "movido",
            event.src_path,
            event.dest_path,
            event.is_directory
        ))


# =========================================================
# RECONCILIAÇÃO COMPLETA DO CATÁLOGO
# =========================================================

def _reconciliar_catalogo():

    logging.info(
        "Iniciando reconciliação do catálogo..."
    )

    if not os.path.isdir(RAIZ_ORIGEM):

        raise FileNotFoundError(
            "Pasta de origem não encontrada ou inacessível: "
            + RAIZ_ORIGEM
        )

    arquivos_encontrados = {}
    erros = []

    def registrar_erro(erro):

        erros.append(erro)

        logging.error(
            "Erro durante a varredura: %s",
            erro
        )

    for raiz, diretorios, arquivos in os.walk(
        RAIZ_ORIGEM,
        onerror=registrar_erro
    ):

        # Aplica os mesmos filtros de pastas do indexador.
        diretorios[:] = [
            nome
            for nome in diretorios
            if nome.lower() not in PASTAS_IGNORADAS
        ]

        for nome in arquivos:

            caminho = normalizar_caminho(
                os.path.join(raiz, nome)
            )

            if caminho_ignorado(caminho):
                continue

            try:

                estat = os.stat(caminho)

                chave = chave_caminho(caminho)

                arquivos_encontrados[chave] = (
                    nome,
                    caminho,
                    os.path.splitext(nome)[1].lower() or None,
                    estat.st_size,
                    estat.st_mtime,
                    estat.st_mtime_ns
                )

            except OSError as erro:

                registrar_erro(erro)

    dados = [
        (
            nome,
            caminho,
            extensao,
            tamanho,
            modificado,
            modificado_ns
        )

        for (
            nome,
            caminho,
            extensao,
            tamanho,
            modificado,
            modificado_ns
        ) in arquivos_encontrados.values()
    ]

    # -----------------------------------------------------
    # Atualiza o catálogo em uma única transação
    # -----------------------------------------------------

    with conectar() as conn:

        conn.executemany(
            """
            INSERT INTO arquivos (
                nome,
                caminho,
                extensao,
                tamanho_bytes,
                modificado_em,
                modificado_ns
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(caminho)
            DO UPDATE SET
                nome = excluded.nome,
                extensao = excluded.extensao,
                tamanho_bytes = excluded.tamanho_bytes,
                modificado_em = excluded.modificado_em,
                modificado_ns = excluded.modificado_ns

            WHERE
                arquivos.nome IS NOT excluded.nome
                OR arquivos.extensao IS NOT excluded.extensao
                OR arquivos.tamanho_bytes IS NOT excluded.tamanho_bytes
                OR arquivos.modificado_em IS NOT excluded.modificado_em
                OR arquivos.modificado_ns IS NOT excluded.modificado_ns
            """,
            dados
        )

        # Só remove registros se a varredura terminou sem erros.
        if not erros:

            prefixo = RAIZ_ORIGEM + os.sep

            registros = conn.execute(
                """
                SELECT caminho
                FROM arquivos
                WHERE substr(caminho, 1, ?) COLLATE NOCASE = ?
                """,
                (len(prefixo), prefixo)
            ).fetchall()

            caminhos_antigos = [
                registro["caminho"]
                for registro in registros
                if chave_caminho(registro["caminho"])
                not in arquivos_encontrados
            ]

            conn.executemany(
                """
                DELETE FROM arquivos
                WHERE caminho = ? COLLATE NOCASE
                """,
                [
                    (caminho,)
                    for caminho in caminhos_antigos
                ]
            )

            logging.info(
                "Registros obsoletos removidos: %s",
                len(caminhos_antigos)
            )

        else:

            logging.warning(
                "Reconciliação parcial: %s erro(s). "
                "Nenhum registro antigo será removido.",
                len(erros)
            )

    logging.info(
        "Reconciliação concluída. "
        "Arquivos encontrados: %s | Erros: %s",
        len(arquivos_encontrados),
        len(erros)
    )


def reconciliar_catalogo():

    with bloqueio_catalogo:
        _reconciliar_catalogo()


# =========================================================
# INICIALIZAÇÃO DO MONITOR
# =========================================================

def iniciar_monitoramento():

    logging.info("Preparando banco de dados...")

    inicializar_banco()
    preparar_indice()

    if not os.path.isdir(RAIZ_ORIGEM):

        raise FileNotFoundError(
            f"Pasta de origem não encontrada: {RAIZ_ORIGEM}"
        )

    manipulador = MonitorDeArquivos()
    observador = Observer()

    observador.schedule(
        manipulador,
        RAIZ_ORIGEM,
        recursive=True
    )

    trabalhador = threading.Thread(
        target=trabalhador_eventos,
        daemon=True
    )

    trabalhador.start()

    try:

        observador.start()

        logging.info("Monitoramento iniciado.")
        logging.info("Pasta monitorada: %s", RAIZ_ORIGEM)
        logging.info(
            "Intervalo de reconciliação: %s horas",
            INTERVALO_RECONCILIACAO / 3600
        )

        # Primeira reconciliação ao iniciar.
        reconciliar_catalogo()

        while True:

            time.sleep(INTERVALO_RECONCILIACAO)

            try:
                reconciliar_catalogo()

            except Exception:

                logging.exception(
                    "Falha durante a reconciliação. "
                    "O monitor continuará em execução."
                )

    except KeyboardInterrupt:

        logging.info(
            "Encerramento solicitado pelo usuário."
        )

    finally:

        logging.info("Encerrando monitoramento...")

        if observador.is_alive():

            observador.stop()
            observador.join()

        fila_eventos.put(None)
        trabalhador.join()

        logging.info(
            "Monitoramento encerrado."
        )


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    iniciar_monitoramento()
