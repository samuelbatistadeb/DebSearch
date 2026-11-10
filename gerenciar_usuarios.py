
from getpass import getpass

from banco import conectar
from usuarios import (
    autenticar_usuario,
    criar_usuario,
    validar_usuario,
    validar_senha,
    gerenciador_senhas
)


# =========================================
# AUTENTICAÇÃO ADMINISTRATIVA
# =========================================

def autenticar_administrador():

    print("\n========================================")
    print("       DEBSEARCH - ADMINISTRAÇÃO")
    print("========================================")

    usuario = input("Usuário administrador: ").strip()
    senha = getpass("Senha: ")

    administrador = autenticar_usuario(usuario, senha)

    if administrador is None:
        print("\nUsuário ou senha inválidos.")
        return None

    if not administrador["administrador"]:
        print("\nAcesso negado. Esta conta não é administradora.")
        return None

    print(
        f"\nAcesso autorizado: {administrador['usuario']}"
    )

    return administrador


# =========================================
# CADASTRAR USUÁRIO
# =========================================

def cadastrar_usuario():

    print("\n========== CADASTRAR USUÁRIO ==========")

    try:

        usuario = input("Novo usuário: ").strip()

        validar_usuario(usuario)

        senha = getpass("Senha inicial: ")
        confirmar = getpass("Confirme a senha: ")

        if senha != confirmar:
            print("\nAs senhas não correspondem.")
            return

        validar_senha(senha)

        resposta = input(
            "Este usuário será administrador? (s/N): "
        ).strip().lower()

        administrador = resposta == "s"

        criar_usuario(
            usuario,
            senha,
            administrador
        )

        print("\nUsuário cadastrado com sucesso.")

    except ValueError as erro:

        print(f"\nNão foi possível cadastrar: {erro}")

    except Exception as erro:

        print(f"\nErro ao cadastrar usuário: {erro}")


# =========================================
# LISTAR USUÁRIOS
# =========================================

def listar_usuarios():

    print("\n========== USUÁRIOS CADASTRADOS ==========")

    with conectar() as conn:

        registros = conn.execute(
            """
            SELECT
                id,
                usuario,
                ativo,
                administrador
            FROM usuarios
            ORDER BY usuario COLLATE NOCASE
            """
        ).fetchall()

    if not registros:
        print("\nNenhum usuário cadastrado.")
        return

    print()

    print(
        f"{'ID':<6}"
        f"{'USUÁRIO':<30}"
        f"{'TIPO':<18}"
        f"{'STATUS':<12}"
    )

    print("-" * 66)

    for registro in registros:

        tipo = (
            "Administrador"
            if registro["administrador"]
            else "Usuário"
        )

        status = (
            "Ativo"
            if registro["ativo"]
            else "Inativo"
        )

        print(
            f"{registro['id']:<6}"
            f"{registro['usuario']:<30}"
            f"{tipo:<18}"
            f"{status:<12}"
        )

    print("-" * 66)

    print(f"Total de usuários: {len(registros)}")


# =========================================
# LOCALIZAR USUÁRIO
# =========================================

def localizar_usuario(usuario):

    with conectar() as conn:

        registro = conn.execute(
            """
            SELECT
                id,
                usuario,
                ativo,
                administrador
            FROM usuarios
            WHERE usuario = ?
            """,
            (usuario,)
        ).fetchone()

    return registro


# =========================================
# DESATIVAR USUÁRIO
# =========================================

def desativar_usuario(administrador_atual):

    print("\n========== DESATIVAR USUÁRIO ==========")

    usuario = input(
        "Usuário que deseja desativar: "
    ).strip()

    registro = localizar_usuario(usuario)

    if registro is None:
        print("\nUsuário não encontrado.")
        return

    if registro["id"] == administrador_atual["id"]:
        print("\nNão é permitido desativar a própria conta.")
        return

    if not registro["ativo"]:
        print("\nEste usuário já está desativado.")
        return

    if registro["administrador"]:

        with conectar() as conn:

            total_administradores = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM usuarios
                WHERE ativo = 1
                AND administrador = 1
                """
            ).fetchone()["total"]

        if total_administradores <= 1:
            print(
                "\nNão é possível desativar o último "
                "administrador ativo."
            )
            return

    print(
        f"\nUsuário: {registro['usuario']}"
    )

    confirmacao = input(
        "Confirma a desativação? (s/N): "
    ).strip().lower()

    if confirmacao != "s":
        print("\nOperação cancelada.")
        return

    with conectar() as conn:

        conn.execute(
            """
            UPDATE usuarios
            SET ativo = 0
            WHERE id = ?
            """,
            (registro["id"],)
        )

    print("\nUsuário desativado com sucesso.")


# =========================================
# REATIVAR USUÁRIO
# =========================================

def reativar_usuario():

    print("\n========== REATIVAR USUÁRIO ==========")

    usuario = input(
        "Usuário que deseja reativar: "
    ).strip()

    registro = localizar_usuario(usuario)

    if registro is None:
        print("\nUsuário não encontrado.")
        return

    if registro["ativo"]:
        print("\nEste usuário já está ativo.")
        return

    confirmacao = input(
        f"Confirma a reativação de {registro['usuario']}? (s/N): "
    ).strip().lower()

    if confirmacao != "s":
        print("\nOperação cancelada.")
        return

    with conectar() as conn:

        conn.execute(
            """
            UPDATE usuarios
            SET ativo = 1
            WHERE id = ?
            """,
            (registro["id"],)
        )

    print("\nUsuário reativado com sucesso.")


# =========================================
# REDEFINIR SENHA
# =========================================

def redefinir_senha():

    print("\n========== REDEFINIR SENHA ==========")

    usuario = input(
        "Usuário que terá a senha redefinida: "
    ).strip()

    registro = localizar_usuario(usuario)

    if registro is None:
        print("\nUsuário não encontrado.")
        return

    senha = getpass("Nova senha: ")
    confirmar = getpass("Confirme a nova senha: ")

    if senha != confirmar:
        print("\nAs senhas não correspondem.")
        return

    try:

        validar_senha(senha)

    except ValueError as erro:

        print(f"\nSenha inválida: {erro}")
        return

    confirmacao = input(
        f"Confirma a redefinição da senha de {registro['usuario']}? (s/N): "
    ).strip().lower()

    if confirmacao != "s":
        print("\nOperação cancelada.")
        return

    novo_hash = gerenciador_senhas.hash(senha)

    with conectar() as conn:

        conn.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?
            WHERE id = ?
            """,
            (novo_hash, registro["id"])
        )

    print("\nSenha redefinida com sucesso.")


# =========================================
# MENU PRINCIPAL
# =========================================

def menu_principal(administrador):

    while True:

        print("\n========================================")
        print("          DEBSEARCH - USUÁRIOS")
        print("========================================")

        print(f"Administrador: {administrador['usuario']}")

        print("\n1 - Cadastrar usuário")
        print("2 - Listar usuários")
        print("3 - Desativar usuário")
        print("4 - Reativar usuário")
        print("5 - Redefinir senha")
        print("0 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()

        try:

            if opcao == "1":
                cadastrar_usuario()

            elif opcao == "2":
                listar_usuarios()

            elif opcao == "3":
                desativar_usuario(administrador)

            elif opcao == "4":
                reativar_usuario()

            elif opcao == "5":
                redefinir_senha()

            elif opcao == "0":
                print("\nEncerrando gerenciamento.")
                break

            else:
                print("\nOpção inválida.")

        except Exception as erro:

            print(f"\nErro durante a operação: {erro}")


# =========================================
# EXECUÇÃO
# =========================================

def main():

    administrador = autenticar_administrador()

    if administrador is None:
        return

    menu_principal(administrador)


if __name__ == "__main__":
    main()
