
import re

from pwdlib import PasswordHash

from banco import conectar


gerenciador_senhas = PasswordHash.recommended()


# Hash fictício utilizado para igualar aproximadamente
# o tempo de resposta quando o usuário não existe.
#
# Gerado uma única vez durante a inicialização do módulo.
HASH_FICTICIO = gerenciador_senhas.hash(
    "senha-ficticia-para-verificacao-interna"
)


def validar_usuario(usuario):
    usuario = usuario.strip()

    if not re.fullmatch(r"[A-Za-z0-9._-]{3,50}", usuario):
        raise ValueError(
            "O usuário deve ter entre 3 e 50 caracteres "
            "e utilizar apenas letras, números, ponto, "
            "hífen ou sublinhado."
        )

    return usuario


def validar_senha(senha):
    if len(senha) < 12:
        raise ValueError(
            "A senha deve possuir pelo menos 12 caracteres."
        )


def criar_usuario(usuario, senha, administrador=False):

    usuario = validar_usuario(usuario)
    validar_senha(senha)

    senha_hash = gerenciador_senhas.hash(senha)

    with conectar() as conn:

        existente = conn.execute(
            """
            SELECT id
            FROM usuarios
            WHERE usuario = ?
            """,
            (usuario,)
        ).fetchone()

        if existente:
            raise ValueError(
                "Este usuário já existe."
            )

        conn.execute(
            """
            INSERT INTO usuarios (
                usuario,
                senha_hash,
                ativo,
                administrador
            )
            VALUES (?, ?, 1, ?)
            """,
            (
                usuario,
                senha_hash,
                int(administrador)
            )
        )

    return True


def autenticar_usuario(usuario, senha):

    usuario = usuario.strip()

    with conectar() as conn:

        registro = conn.execute(
            """
            SELECT
                id,
                usuario,
                senha_hash,
                ativo,
                administrador
            FROM usuarios
            WHERE usuario = ?
            """,
            (usuario,)
        ).fetchone()

    # Usuário inexistente:
    # executa Argon2 com um hash fictício.
    if registro is None:

        gerenciador_senhas.verify(
            senha,
            HASH_FICTICIO
        )

        return None

    # Usuário existente:
    # executa a verificação real antes de avaliar
    # se a conta está ativa.
    senha_valida = gerenciador_senhas.verify(
        senha,
        registro["senha_hash"]
    )

    if not registro["ativo"]:
        return None

    if not senha_valida:
        return None

    return {
        "id": registro["id"],
        "usuario": registro["usuario"],
        "administrador": bool(
            registro["administrador"]
        )
    }


def obter_usuario(usuario_id):

    with conectar() as conn:

        registro = conn.execute(
            """
            SELECT
                id,
                usuario,
                administrador
            FROM usuarios
            WHERE id = ? AND ativo = 1
            """,
            (usuario_id,)
        ).fetchone()

    if registro is None:
        return None

    return {
        "id": registro["id"],
        "usuario": registro["usuario"],
        "administrador": bool(
            registro["administrador"]
        )
    }
