"""Configurações do Catálogo de Notas Fiscais."""
from pathlib import Path

# Pasta compartilhada original. O indexador apenas LÊ os documentos.
PASTA_ORIGEM = Path(r"YOUR PATH\TO\SHARED\FOLDER")

# None = catalogar todos os arquivos; ou use {".pdf", ".xml"} para restringir.
EXTENSOES_PERMITIDAS = None

PASTAS_IGNORADAS = {"$recycle.bin", "system volume information"}
PREFIXOS_IGNORADOS = ("~$",)
EXTENSOES_IGNORADAS = {".tmp", ".temp", ".part", ".crdownload"}
