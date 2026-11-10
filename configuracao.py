"""Configurações do Catálogo de Notas Fiscais."""
from pathlib import Path
import os
# Pasta compartilhada original. O indexador apenas LÊ os documentos.
PASTA_ORIGEM = Path(r"YOUR PATH\TO\SHARED\FOLDER")

# None = catalogar todos os arquivos; ou use {".pdf", ".xml"} para restringir.
EXTENSOES_PERMITIDAS = None

PASTAS_IGNORADAS = {"$recycle.bin", "system volume information"}
PREFIXOS_IGNORADOS = ("~$",)
EXTENSOES_IGNORADAS = {".tmp", ".temp", ".part", ".crdownload"}

# Autenticação e sessões do DebDocs
DEBDOCS_SECRET_KEY = os.getenv("DEBDOCS_SECRET_KEY")

# Duração máxima da sessão: 8 horas
TEMPO_SESSAO_SEGUNDOS = 8 * 60 * 60

# Durante os testes locais, utilizaremos HTTP.
# Ao configurar HTTPS na rede, alteraremos para True.
COOKIE_SEGURO = False