""" Extração dos dados da página de busca. """

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from . import config

logger = logging.getLogger(__name__)


def _melhor_conjunto(soup: BeautifulSoup, seletores: list[str]):
    """ 
    Tenta cada seletor candidato e devolve o conjunto com mais
    elementos encontrados.
    """
    melhor_seletor = None
    elementos_encontrados: list[Tag] = []
    for seletor in seletores:
        encontrados = soup.select(seletor)
        if len(encontrados) > len(elementos_encontrados):
            melhor_seletor = seletor
            elementos_encontrados = encontrados
    return melhor_seletor, elementos_encontrados


def _extrair_texto(card: Tag, seletores: list[str]) -> Optional[str]:
    """ Extrai os textos necessários da notícia. """
    for seletor in seletores:
        elemento = card.select_one(seletor)
        if elemento:
            texto = elemento.get_text(strip=True)
            if texto:
                return texto
    return None


def _extrair_link(card: Tag, seletores: list[str], url_base: str) -> Optional[str]:
    """ Extrai a url da notícia. """
    for seletor in seletores:
        elemento = card.select_one(seletor)
        if elemento and elemento.get("href"):
            url_absoluta = urljoin(url_base, elemento["href"])
            partes = urlparse(url_absoluta)
            if "measures.globo.com" not in partes.netloc:
                return url_absoluta
        
            destino = parse_qs(partes.query).get("u", [None])[0]
            return destino if destino else url_absoluta
    return None


def parse_pagina(html: str, lote: int, url_pagina: str) -> list[dict]:
    """ Extrai a lista de resultados de um lote de HTML. """
    soup = BeautifulSoup(html, "html.parser")

    # localiza os elementos resultantes da busca na página
    seletor_usado, cards = _melhor_conjunto(soup, config.SELECTORS["card"])

    dados: list[dict] = []

    if cards:
        logger.debug("Seletor de card em uso: %s (%d encontrados)", seletor_usado, len(cards))
        for card in cards:
            titulo = _extrair_texto(card, config.SELECTORS["titulo"])
            resumo = _extrair_texto(card, config.SELECTORS["resumo"])
            data_publicacao = _extrair_texto(card, config.SELECTORS["data"])
            link = _extrair_link(card, config.SELECTORS["link"], url_pagina)

            if not titulo and not link:
                continue

            for nome_campo, valor in (
                ("título", titulo), ("url", link), ("resumo", resumo), ("data", data_publicacao)
            ):
                if valor is None:
                    logger.debug("Campo '%s' ausente em um card do lote %d", nome_campo, lote)

            dados.append(
                {
                    "titulo": titulo,
                    "url": link,
                    "resumo": resumo,
                    "data_publicacao": data_publicacao,
                }
            )
    else:
        logger.warning("Nenhum card encontrado com os seletores configurados no lote %d.", lote,)

    return dados
