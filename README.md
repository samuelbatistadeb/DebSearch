# Catálogo de Notas Fiscais — Etapa 1

## Objetivo
Criar a estrutura inicial do banco SQLite. Nesta etapa ainda não há leitura,
movimentação, exclusão ou alteração dos PDFs da pasta compartilhada.

## Requisitos
- Windows
- Python 3.10 ou superior (recomendado)
- Nenhuma biblioteca externa; usamos apenas a biblioteca padrão `sqlite3`.

## Como executar no VS Code

1. Extraia esta pasta em um local de trabalho.
2. Abra a pasta `catalogo_notas_etapa1` no VS Code.
3. Ative seu ambiente virtual, se já tiver um:
   - PowerShell: `.venv\\Scripts\\Activate.ps1`
4. Execute:
   `python banco.py`
5. Execute o teste:
   `python teste_banco.py`

O banco será criado em `database/catalogo.db`.

## Estrutura da tabela `arquivos`

- `id`: identificador interno.
- `nome`: nome do arquivo.
- `caminho`: caminho completo do arquivo; único para evitar duplicidade.
- `extensao`: extensão, como `.pdf` ou `.xml`.
- `tamanho_bytes`: tamanho do arquivo.
- `modificado_em`: data de modificação em formato timestamp.
- `modificado_ns`: timestamp de alta precisão para detectar alterações.
- `cadastrado_em`: data em que o registro foi inserido no catálogo.

## Importante sobre a implantação

Durante o desenvolvimento, o banco fica dentro desta pasta do projeto.
Na implantação, o banco deve ficar no disco local do computador servidor
(192.168.0.134), e a aplicação de pesquisa consultará o banco por meio da
aplicação web. Não coloque o arquivo SQLite em uma pasta de rede SMB para
vários computadores abrirem diretamente.

O caminho da pasta original de notas fiscais será configurado na próxima etapa.
Este código ainda não acessa essa pasta.
