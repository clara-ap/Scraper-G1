"""
Organização da coleta de dados. Abre a página de busca do G1 e vai
consumindo os lotes de resultados que aparecem conforme o Playwright
clica em "Veja mais", aplicando o parser a cada lote.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from . import config
from .parser import parse_pagina
from .playwright_client import renderizar_pagina

logger = logging.getLogger(__name__)


def montar_url(termo_busca: str) -> str:
    """ Monta a URL de busca do G1 para o termo informado. """
    return f"{config.URL_BASE}?q={termo_busca}"


def _chave_dedup(item: dict) -> str:
    """ Chave (URL) usada para identificar duplicados. """
    
    url = item.get("url")
    if url:
        return re.sub(r"[?#].*$", "", url).rstrip("/")
    return f"{item.get('titulo', '')}|{item.get('data_publicacao', '')}"


def coletar(termo_busca: str = config.TERMO_BUSCA_PADRAO) -> list[dict]:
    """
    Coleta resultados de busca do G1 para o termo informado.

    Abre a página de busca e consome os lotes de resultados que vão
    aparecendo conforme o Playwright clica em "Veja mais".
    """
    url_busca = montar_url(termo_busca)
    logger.info("Iniciando coleta: %s", url_busca)

    resultados: list[dict] = []
    chaves_vistas: set[str] = set()

    for lote, html in enumerate(renderizar_pagina(url_busca), start=1):
        dados_lote = parse_pagina(html, lote, url_busca)

        novos_no_lote = 0
        for item in dados_lote:
            chave = _chave_dedup(item)
            if chave in chaves_vistas:
                continue
            chaves_vistas.add(chave)
            novos_no_lote += 1
            resultados.append(
                {
                    "titulo": item.get("titulo"),
                    "url": item.get("url"),
                    "resumo": item.get("resumo"),
                    "data_publicacao": item.get("data_publicacao"),
                    "lote": lote,
                    "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )

        logger.info(
            "Lote %d: %d resultado(s) novo(s) | %d no total até agora.",
            lote, novos_no_lote, len(resultados),
        )

    if not resultados:
        logger.warning(
            "Nenhum lote de resultados foi obtido. Verifique se o Playwright/Chromium "
            "está instalado e se a busca realmente tem resultados para o termo '%s'.",
            termo_busca,
        )

    logger.info("Coleta finalizada: %d resultado(s) único(s).", len(resultados))
    return resultados
