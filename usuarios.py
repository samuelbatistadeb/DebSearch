
"""
Gerenciamento de usuários e autenticação do DebDocs.
As senhas são armazenadas usando hash Argon2.
"""

import re

from pwdlib import PasswordHash

from banco import conectar


gerenciador_senhas = PasswordHash.recommended()


def validar_usuario(usuario):
    usuario = usuario.strip()

    if not re.fullmatch(r"[A-Za-z0-9._-]{3,50}", usuario):
        raise ValueError(
            "O usuário deve ter entre 3 e 50 caracteres, "
            "utilizando apenas letras, números, ponto, "
            "hífen ou sublinhado."
        )

    return usuario


def validar_senha(senha):
    if len(senha) < 12:
        raise ValueError(
            "A senha deve possuir pelo menos 12 caracteres."
        )


def criar_usuario(usuario, senha, administrador=False):
    """Cadastra um usuário com senha protegida por Argon2."""

    usuario = validar_usuario(usuario)
    validar_senha(senha)

    senha_hash = gerenciador_senhas.hash(senha)

    with conectar() as conn:
        existente = conn.execute(
            "SELECT id FROM usuarios WHERE usuario = ?",
            (usuario,)
        ).fetchone()

        if existente:
            raise ValueError("Esse usuário já está cadastrado.")

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
            (usuario, senha_hash, int(administrador))
        )

    return True


def autenticar_usuario(usuario, senha):
    """Verifica as credenciais e retorna os dados do usuário."""

    usuario = usuario.strip()

    with conectar() as conn:
        registro = conn.execute(
            """
            SELECT id, usuario, senha_hash, ativo, administrador
            FROM usuarios
            WHERE usuario = ?
            """,
            (usuario,)
        ).fetchone()

    if registro is None:
        return None

    if not registro["ativo"]:
        return None

    if not gerenciador_senhas.verify(
        senha,
        registro["senha_hash"]
    ):
        return None

    return {
        "id": registro["id"],
        "usuario": registro["usuario"],
        "administrador": bool(registro["administrador"])
    }


def obter_usuario(usuario_id):
    """Retorna os dados públicos de um usuário ativo."""

    with conectar() as conn:
        registro = conn.execute(
            """
            SELECT id, usuario, administrador
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
        "administrador": bool(registro["administrador"])
    }
