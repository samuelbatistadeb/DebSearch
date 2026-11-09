
import os
import time
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from configuracao import PASTA_ORIGEM
from banco import conectar, inicializar_banco


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def arquivo_ignorado(caminho):
    nome = os.path.basename(caminho).lower()

    ignorados = (
        nome.startswith("~$"),
        nome.endswith(".tmp"),
        nome.endswith(".part"),
        nome.endswith(".crdownload"),
    )

    return any(ignorados)


def aguardar_arquivo_estavel(caminho, tentativas=10, intervalo=1):
    tamanho_anterior = None
    estavel = 0

    for _ in range(tentativas):
        try:
            if not os.path.isfile(caminho):
                return False

            tamanho_atual = os.path.getsize(caminho)

            if tamanho_atual == tamanho_anterior:
                estavel += 1
            else:
                estavel = 0

            if estavel >= 2:
                return True

            tamanho_anterior = tamanho_atual

        except OSError:
            estavel = 0

        time.sleep(intervalo)

    return False


def cadastrar_ou_atualizar(caminho):
    caminho = os.path.abspath(caminho)

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
        logging.error("Erro ao acessar arquivo %s: %s", caminho, erro)


def remover_arquivo(caminho):
    caminho = os.path.abspath(caminho)

    with conectar() as conn:
        conn.execute(
            "DELETE FROM arquivos WHERE caminho = ?",
            (caminho,)
        )

    logging.info("Registro removido: %s", caminho)


def indexar_pasta(caminho):
    if not os.path.isdir(caminho):
        return

    for raiz, diretorios, arquivos in os.walk(caminho):
        for nome in arquivos:
            cadastrar_ou_atualizar(
                os.path.join(raiz, nome)
            )


def atualizar_caminho_pasta(origem, destino):
    """
    Atualiza os caminhos de todos os registros de uma pasta
    e de suas subpastas.
    """

    origem = os.path.abspath(origem)
    destino = os.path.abspath(destino)

    prefixo = origem + os.sep

    with conectar() as conn:
        registros = conn.execute("""
            SELECT caminho FROM arquivos
            WHERE substr(caminho, 1, ?) = ?
        """, (len(prefixo), prefixo)).fetchall()

        for registro in registros:
            caminho_antigo = registro[0]

            relativo = os.path.relpath(
                caminho_antigo,
                origem
            )

            caminho_novo = os.path.join(
                destino,
                relativo
            )

            if os.path.exists(caminho_novo):
                cadastrar_ou_atualizar(caminho_novo)

            remover_arquivo(caminho_antigo)


class MonitorDeArquivos(FileSystemEventHandler):

    def on_created(self, event):
        if event.is_directory:
            logging.info("Pasta criada: %s", event.src_path)
            indexar_pasta(event.src_path)
        else:
            cadastrar_ou_atualizar(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            cadastrar_ou_atualizar(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            prefixo = os.path.abspath(event.src_path) + os.sep

            with conectar() as conn:
                conn.execute("""
                    DELETE FROM arquivos
                    WHERE substr(caminho, 1, ?) = ?
                """, (len(prefixo), prefixo))

            logging.info("Registros da pasta removidos.")

        else:
            remover_arquivo(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            atualizar_caminho_pasta(
                event.src_path,
                event.dest_path
            )

        else:
            remover_arquivo(event.src_path)
            cadastrar_ou_atualizar(event.dest_path)


def iniciar_monitoramento():

    inicializar_banco()

    if not os.path.isdir(PASTA_ORIGEM):
        raise FileNotFoundError(
            f"Pasta não encontrada: {PASTA_ORIGEM}"
        )

    observador = Observer()
    manipulador = MonitorDeArquivos()

    observador.schedule(
        manipulador,
        PASTA_ORIGEM,
        recursive=True
    )

    observador.start()

    logging.info("Monitoramento iniciado.")
    logging.info("Pasta: %s", PASTA_ORIGEM)

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Encerrando monitoramento...")
        observador.stop()

    observador.join()


if __name__ == "__main__":
    iniciar_monitoramento()
