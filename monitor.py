
import os
import time
import queue
import logging
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from configuracao import PASTA_ORIGEM
from banco import conectar, inicializar_banco


# Reconciliação a cada 24 horas
INTERVALO_RECONCILIACAO = 24 * 60 * 60

# Agrupamento de eventos recebidos em sequência
TEMPO_AGRUPAMENTO = 1


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


fila_eventos = queue.Queue()


def caminho_absoluto(caminho):
    return os.path.normcase(os.path.abspath(caminho))


def arquivo_ignorado(caminho):
    nome = os.path.basename(caminho).lower()

    return (
        nome.startswith("~$")
        or nome.endswith(".tmp")
        or nome.endswith(".part")
        or nome.endswith(".crdownload")
    )


def aguardar_arquivo_estavel(caminho, tentativas=10, intervalo=1):
    tamanho_anterior = None
    repeticoes = 0

    for _ in range(tentativas):
        try:
            if not os.path.isfile(caminho):
                return False

            tamanho_atual = os.path.getsize(caminho)

            if tamanho_atual == tamanho_anterior:
                repeticoes += 1
            else:
                repeticoes = 0

            if repeticoes >= 2:
                return True

            tamanho_anterior = tamanho_atual

        except OSError:
            repeticoes = 0

        time.sleep(intervalo)

    return False


def cadastrar_ou_atualizar(caminho):
    caminho = caminho_absoluto(caminho)

    if arquivo_ignorado(caminho):
        return

    if not aguardar_arquivo_estavel(caminho):
        logging.warning("Arquivo não estabilizou: %s", caminho)
        return

    try:
        nome = os.path.basename(caminho)
        extensao = os.path.splitext(nome)[1].lower()
        estat = os.stat(caminho)

        with conectar() as conn:
            conn.execute("""
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
            """, (
                nome,
                caminho,
                extensao,
                estat.st_size,
                estat.st_mtime,
                estat.st_mtime_ns
            ))

        logging.info("Cadastrado/atualizado: %s", caminho)

    except OSError as erro:
        logging.error("Erro ao acessar %s: %s", caminho, erro)


def remover_arquivo(caminho):
    caminho = caminho_absoluto(caminho)

    with conectar() as conn:
        conn.execute(
            "DELETE FROM arquivos WHERE caminho = ?",
            (caminho,)
        )

    logging.info("Registro removido: %s", caminho)


def remover_pasta(caminho):
    prefixo = caminho_absoluto(caminho) + os.sep

    with conectar() as conn:
        conn.execute("""
            DELETE FROM arquivos
            WHERE substr(caminho, 1, ?) = ?
        """, (len(prefixo), prefixo))

    logging.info("Registros da pasta removidos: %s", caminho)


def indexar_pasta(caminho):
    if not os.path.isdir(caminho):
        return

    for raiz, diretorios, arquivos in os.walk(caminho):
        for nome in arquivos:
            cadastrar_ou_atualizar(
                os.path.join(raiz, nome)
            )


def processar_eventos(eventos):
    """
    Agrupa eventos repetidos para evitar operações desnecessárias.
    """

    acoes_arquivos = {}
    acoes_pastas = []

    for tipo, origem, destino, eh_diretorio in eventos:

        if eh_diretorio:
            acoes_pastas.append(
                (tipo, origem, destino)
            )
            continue

        if tipo == "movido":
            acoes_arquivos[caminho_absoluto(origem)] = (
                "remover",
                origem
            )

            acoes_arquivos[caminho_absoluto(destino)] = (
                "atualizar",
                destino
            )

        elif tipo == "excluido":
            acoes_arquivos[caminho_absoluto(origem)] = (
                "remover",
                origem
            )

        else:
            acoes_arquivos[caminho_absoluto(origem)] = (
                "atualizar",
                origem
            )

    # Processa movimentações, criações e exclusões de pastas
    for tipo, origem, destino in acoes_pastas:

        if tipo == "criado":
            indexar_pasta(origem)

        elif tipo == "excluido":
            remover_pasta(origem)

        elif tipo == "movido":
            remover_pasta(origem)
            indexar_pasta(destino)

    # Processa os arquivos, sem repetir ações para o mesmo caminho
    for acao, caminho in acoes_arquivos.values():

        if acao == "remover":
            remover_arquivo(caminho)

        elif acao == "atualizar":
            cadastrar_ou_atualizar(caminho)


def trabalhador_eventos():
    logging.info("Fila de eventos iniciada.")

    while True:
        primeiro = fila_eventos.get()

        if primeiro is None:
            break

        eventos = [primeiro]

        # Aguarda brevemente para agrupar eventos semelhantes
        time.sleep(TEMPO_AGRUPAMENTO)

        while True:
            try:
                evento = fila_eventos.get_nowait()

                if evento is None:
                    return

                eventos.append(evento)

            except queue.Empty:
                break

        try:
            processar_eventos(eventos)

        except Exception:
            logging.exception("Erro ao processar eventos da fila.")


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


def reconciliar_catalogo():
    """
    Compara a pasta física com o banco.

    Só remove registros antigos se a varredura terminar
    sem erros de leitura.
    """

    logging.info("Iniciando reconciliação do catálogo...")

    arquivos_encontrados = {}
    erros = []

    def registrar_erro(erro):
        erros.append(erro)
        logging.error("Erro durante a varredura: %s", erro)

    for raiz, diretorios, arquivos in os.walk(
        PASTA_ORIGEM,
        onerror=registrar_erro
    ):

        for nome in arquivos:
            caminho = caminho_absoluto(
                os.path.join(raiz, nome)
            )

            if arquivo_ignorado(caminho):
                continue

            try:
                estat = os.stat(caminho)

                arquivos_encontrados[caminho] = (
                    nome,
                    os.path.splitext(nome)[1].lower(),
                    estat.st_size,
                    estat.st_mtime,
                    estat.st_mtime_ns
                )

            except OSError as erro:
                registrar_erro(erro)

    # Cadastra e atualiza os arquivos encontrados
    dados = [
        (
            nome,
            caminho,
            extensao,
            tamanho,
            modificado,
            modificado_ns
        )
        for caminho, (
            nome,
            extensao,
            tamanho,
            modificado,
            modificado_ns
        ) in arquivos_encontrados.items()
    ]

    with conectar() as conn:
        conn.executemany("""
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
        """, dados)

    # Só exclui registros antigos se a leitura foi completa
    if erros:
        logging.warning(
            "Reconciliação parcial. Nenhum registro foi excluído."
        )
    else:
        raiz = caminho_absoluto(PASTA_ORIGEM)
        prefixo = raiz + os.sep

        with conectar() as conn:
            registros = conn.execute("""
                SELECT caminho
                FROM arquivos
                WHERE substr(caminho, 1, ?) = ?
            """, (len(prefixo), prefixo)).fetchall()

            caminhos_antigos = [
                registro[0]
                for registro in registros
                if caminho_absoluto(registro[0])
                not in arquivos_encontrados
            ]

            conn.executemany("""
                DELETE FROM arquivos
                WHERE caminho = ?
            """, [(caminho,) for caminho in caminhos_antigos])

        logging.info(
            "Registros obsoletos removidos: %s",
            len(caminhos_antigos)
        )

    logging.info(
        "Reconciliação concluída. Arquivos encontrados: %s",
        len(arquivos_encontrados)
    )


def iniciar_monitoramento():

    inicializar_banco()

    if not os.path.isdir(PASTA_ORIGEM):
        raise FileNotFoundError(
            f"Pasta não encontrada: {PASTA_ORIGEM}"
        )

    manipulador = MonitorDeArquivos()
    observador = Observer()

    observador.schedule(
        manipulador,
        PASTA_ORIGEM,
        recursive=True
    )

    # Inicia a fila antes do observador
    trabalhador = threading.Thread(
        target=trabalhador_eventos,
        daemon=True
    )
    trabalhador.start()

    observador.start()

    logging.info("Monitoramento iniciado.")
    logging.info("Pasta: %s", PASTA_ORIGEM)

    try:
        # Reconciliação inicial
        reconciliar_catalogo()

        while True:
            time.sleep(INTERVALO_RECONCILIACAO)

            reconciliar_catalogo()

    except KeyboardInterrupt:
        logging.info("Encerrando monitoramento...")

    finally:
        observador.stop()
        observador.join()

        fila_eventos.put(None)
        trabalhador.join()

        logging.info("Monitoramento encerrado.")


if __name__ == "__main__":
    iniciar_monitoramento()
