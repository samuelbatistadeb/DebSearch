
"""
Criação inicial do administrador do DebSearch.
Executado localmente pelo terminal.
"""

from getpass import getpass

from banco import inicializar_banco, conectar
from usuarios import criar_usuario


def main():
    inicializar_banco()

    # Impede a criação de outro administrador pelo procedimento inicial.
    with conectar() as conn:
        quantidade = conn.execute(
            """
            SELECT COUNT(*)
            FROM usuarios
            WHERE administrador = 1
            """
        ).fetchone()[0]

    if quantidade > 0:
        print("Já existe um administrador cadastrado.")
        print("Use a administração do sistema para gerenciar usuários.")
        return

    print("=" * 45)
    print("CADASTRO DO ADMINISTRADOR - DEBSEARCH")
    print("=" * 45)

    usuario = input("\nNome de usuário: ").strip()

    senha = getpass("Digite a senha: ")
    confirmacao = getpass("Confirme a senha: ")

    if senha != confirmacao:
        print("\nAs senhas não são iguais.")
        return

    try:
        criar_usuario(
            usuario=usuario,
            senha=senha,
            administrador=True
        )

        print("\nAdministrador cadastrado com sucesso!")

    except ValueError as erro:
        print(f"\nNão foi possível cadastrar: {erro}")


if __name__ == "__main__":
    main()
