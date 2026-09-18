""" Este módulo concentra parâmetros centrais do scraper de busca do G1. """

from __future__ import annotations

URL_BASE = "https://g1.globo.com/busca/"
TERMO_BUSCA_PADRAO = "lgpd"

# Identificando aba como um navegador Chrome comum
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

PLAYWRIGHT_TIMEOUT_MS = 15_000
PLAYWRIGHT_MAX_ROLAGENS = 150         # limite de cliques em "Veja mais"
PLAYWRIGHT_INTERVALO_POLL_MS = 500   
PLAYWRIGHT_TIMEOUT_CARREGAMENTO_MS = 10_000 
PLAYWRIGHT_CHECAGENS_ESTAVEIS = 2     # nº de tentativas seguidas sem crescimento para considerar "carregou tudo"

PLAYWRIGHT_TEXTO_BOTAO_CARREGAR_MAIS = "Veja mais"

# Como a estrutura HTML do site pode ser modificada, os seletores abaixo 
# são listas ordenadas por prioridade: o parser tenta cada seletor da 
# lista, em ordem, até encontrar resultado.
# Rode com --log DEBUG, veja o que o parser encontra, e ajuste aqui.
SELECTORS = {
    "card": [
        "div.widget--info",
        "li.widget--card",
        "div.resultado-busca-item",
        "div[class*='busca'][class*='resultado']",
        "article",
    ],
    "titulo": [
        ".widget--info__title",
        ".widget--card__title",
        "h2",
        "h3",
    ],
    "resumo": [
        ".widget--info__description",
        ".widget--card__description",
        "p",
    ],
    "data": [
        ".widget--info__meta-date",
        ".widget--card__meta-date",
        "time",
        "span[class*='data']",
    ],
    "link": [
        "a.widget--info__text-container",
        "a.widget--card__link",
        "a",
    ],
}

CAMPOS_SAIDA = [
    "titulo",
    "url",
    "resumo",
    "data_publicacao",
    "lote",
    "coletado_em",
]
