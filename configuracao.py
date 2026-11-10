"""Configurações do DebSearch."""

from pathlib import Path
import os

# =====================================
# PASTA DE ORIGEM
# =====================================

PASTA_ORIGEM = Path(
    r"YOUR PATH\TO\SHARED\FOLDER"
)

# =====================================
# FILTROS DE ARQUIVOS
# =====================================

EXTENSOES_PERMITIDAS = None

PASTAS_IGNORADAS = {
    "$recycle.bin",
    "system volume information"
}

PREFIXOS_IGNORADOS = ("~$",)

EXTENSOES_IGNORADAS = {
    ".tmp",
    ".temp",
    ".part",
    ".crdownload"
}

# =====================================
# AUTENTICAÇÃO E SESSÕES
# =====================================

DEBSEARCH_SECRET_KEY = os.getenv("DEBSEARCH_SECRET_KEY")

TEMPO_SESSAO_SEGUNDOS = 8 * 60 * 60

# False durante testes HTTP.
# True após configurar HTTPS.
COOKIE_SEGURO = False