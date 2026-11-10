
import time

from banco import conectar


# Configurações da proteção
MAX_TENTATIVAS = 5
JANELA_TENTATIVAS = 15 * 60  # 15 minutos

BLOQUEIO_INICIAL = 60       # 1 minuto
BLOQUEIO_MAXIMO = 60 * 60   # 1 hora

TEMPO_LIMPEZA = 30 * 24 * 60 * 60  # 30 dias


def normalizar_identificador(usuario):
    """
    Normaliza o nome do usuário para evitar que diferenças
    entre maiúsculas e minúsculas criem contagens separadas.
    """
    return usuario.strip().casefold()


def obter_ip_cliente(request):
    """
    Obtém o IP diretamente da conexão.

    Não utiliza X-Forwarded-For, pois esse cabeçalho pode
    ser falsificado quando não existe proxy confiável.
    """
    if request.client and request.client.host:
        return request.client.host

    return "ip-desconhecido"


def consultar_bloqueio(ip, usuario):
    """
    Verifica se a combinação IP + usuário está bloqueada.

    Retorna:
        None: se não houver bloqueio ativo.
        Dicionário: se houver bloqueio ativo.
    """
    identificador = normalizar_identificador(usuario)
    agora = time.time()

    with conectar() as conn:
        registro = conn.execute(
            """
            SELECT bloqueado_ate
            FROM tentativas_login
            WHERE ip = ? AND usuario_normalizado = ?
            """,
            (ip, identificador)
        ).fetchone()

    if registro is None or registro["bloqueado_ate"] is None:
        return None

    restante = registro["bloqueado_ate"] - agora

    if restante <= 0:
        return None

    return {
        "bloqueado": True,
        "segundos_restantes": int(restante) + 1
    }


def registrar_falha(ip, usuario):
    """
    Registra uma tentativa malsucedida.

    Após cinco falhas dentro da janela de 15 minutos,
    aplica um bloqueio progressivo.

    Retorna informações sobre o estado da proteção.
    """
    identificador = normalizar_identificador(usuario)
    agora = time.time()

    with conectar() as conn:
        conn.execute("BEGIN IMMEDIATE")

        registro = conn.execute(
            """
            SELECT falhas,
                   inicio_janela,
                   bloqueado_ate,
                   nivel_bloqueio
            FROM tentativas_login
            WHERE ip = ? AND usuario_normalizado = ?
            """,
            (ip, identificador)
        ).fetchone()

        if registro is not None:
            bloqueado_ate = registro["bloqueado_ate"]

            if bloqueado_ate is not None and bloqueado_ate > agora:
                return {
                    "bloqueado": True,
                    "segundos_restantes": int(bloqueado_ate - agora) + 1
                }

        if registro is None:
            falhas = 1
            inicio_janela = agora
            nivel_bloqueio = 0

            conn.execute(
                """
                INSERT INTO tentativas_login (
                    ip,
                    usuario_normalizado,
                    falhas,
                    inicio_janela,
                    bloqueado_ate,
                    nivel_bloqueio,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    ip,
                    identificador,
                    falhas,
                    inicio_janela,
                    nivel_bloqueio,
                    agora
                )
            )

        else:
            falhas = registro["falhas"]
            inicio_janela = registro["inicio_janela"]
            nivel_bloqueio = registro["nivel_bloqueio"]

            # Reinicia a contagem se a janela de 15 minutos expirou.
            if (
                inicio_janela is None
                or agora - inicio_janela > JANELA_TENTATIVAS
            ):
                falhas = 1
                inicio_janela = agora
            else:
                falhas += 1

            conn.execute(
                """
                UPDATE tentativas_login
                SET falhas = ?,
                    inicio_janela = ?,
                    bloqueado_ate = NULL,
                    atualizado_em = ?
                WHERE ip = ? AND usuario_normalizado = ?
                """,
                (
                    falhas,
                    inicio_janela,
                    agora,
                    ip,
                    identificador
                )
            )

        if falhas >= MAX_TENTATIVAS:
            nivel_bloqueio += 1

            duracao = min(
                BLOQUEIO_INICIAL * (2 ** (nivel_bloqueio - 1)),
                BLOQUEIO_MAXIMO
            )

            bloqueado_ate = agora + duracao

            conn.execute(
                """
                UPDATE tentativas_login
                SET falhas = 0,
                    inicio_janela = NULL,
                    bloqueado_ate = ?,
                    nivel_bloqueio = ?,
                    atualizado_em = ?
                WHERE ip = ? AND usuario_normalizado = ?
                """,
                (
                    bloqueado_ate,
                    nivel_bloqueio,
                    agora,
                    ip,
                    identificador
                )
            )

            return {
                "bloqueado": True,
                "segundos_restantes": duracao,
                "nivel_bloqueio": nivel_bloqueio
            }

        return {
            "bloqueado": False,
            "falhas": falhas,
            "tentativas_restantes": MAX_TENTATIVAS - falhas
        }


def registrar_sucesso(ip, usuario):
    """
    Remove o histórico de falhas após um login bem-sucedido.
    """
    identificador = normalizar_identificador(usuario)

    with conectar() as conn:
        conn.execute(
            """
            DELETE FROM tentativas_login
            WHERE ip = ? AND usuario_normalizado = ?
            """,
            (ip, identificador)
        )


def limpar_registros_antigos():
    """
    Remove registros sem atualização há mais de 30 dias.
    """
    limite = time.time() - TEMPO_LIMPEZA

    with conectar() as conn:
        resultado = conn.execute(
            """
            DELETE FROM tentativas_login
            WHERE atualizado_em < ?
            """,
            (limite,)
        )

        return resultado.rowcount
