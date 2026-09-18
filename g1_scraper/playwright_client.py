"""
Cliente baseado em Playwright.

Implementado porque a página de busca do G1 devolve um contêiner vazio 
(div.results__content.all-search-results) no HTML estático. Os
resultados são renderizados inteiramente via JavaScript no navegador.
"""

from __future__ import annotations

import logging
from typing import Iterator
from playwright.sync_api import sync_playwright

from . import config

logger = logging.getLogger(__name__)

# Seletor do contêiner que o React preenche com os resultados
SELETOR_CONTAINER_RESULTADOS = "div.all-search-results"

_JS_CONTAR_ITENS = """
(seletores) => {
    let maximo = 0;
    for (const seletor of seletores) {
        const quantidade = document.querySelectorAll(seletor).length;
        if (quantidade > maximo) {
            maximo = quantidade;
        }
    }
    return maximo;
}
"""

def _carregar_mais(pagina) -> bool:
    """ Tenta carregar mais resultados clicando em "Veja Mais". """
    texto = config.PLAYWRIGHT_TEXTO_BOTAO_CARREGAR_MAIS
    try:
        # tenta achar <button> com "Veja Mais"
        botao = pagina.get_by_role("button", name=texto, exact=False).last
        if botao.is_visible(timeout=800):
            botao.scroll_into_view_if_needed(timeout=2000)
            botao.click(timeout=2000)
            return True
    except Exception:
        pass

    try:
        # tenta achar qualquer elemento com "Veja Mais"
        botao = pagina.get_by_text(texto, exact=False).last
        if botao.is_visible(timeout=1500):
            botao.scroll_into_view_if_needed(timeout=2000)
            botao.click(timeout=2000)
            return True
    except Exception:
        pass
    return False


def _esperar_crescer(pagina, contagem_anterior: int) -> int:
    """
    Espera antes de contar novamente a quantidade de itens na página,
    pois depois de clicar em "Veja mais", o próximo lote de resultados 
    pode demorar para chegar.
    """
    tempo_decorrido_ms = 0
    contagem_atual = contagem_anterior
    while tempo_decorrido_ms < config.PLAYWRIGHT_TIMEOUT_CARREGAMENTO_MS:
        pagina.wait_for_timeout(config.PLAYWRIGHT_INTERVALO_POLL_MS)
        tempo_decorrido_ms += config.PLAYWRIGHT_INTERVALO_POLL_MS
        contagem_atual = pagina.evaluate(_JS_CONTAR_ITENS, config.SELECTORS["card"])
        if contagem_atual > contagem_anterior:
            return contagem_atual
    return contagem_atual


def _iterar_carregamentos(pagina) -> Iterator[str]:
    """
    Dado um objeto "pagina" já navegado e com o primeiro lote de 
    resultados visível, retorna pagina.content() logo de início. 
    Retorna o HTML de novo a cada tentativa de clicar em "Veja mais" 
    que resulte em mais itens no contêiner.

    Para quando a quantidade de itens na página estabiliza por
    config.PLAYWRIGHT_CHECAGENS_ESTAVEIS tentativas seguidas, ou ao
    atingir config.PLAYWRIGHT_MAX_ROLAGENS tentativas no total.
    """

    # contagem de itens antes do primeiro "Veja Mais"
    contagem_anterior = pagina.evaluate(_JS_CONTAR_ITENS, config.SELECTORS["card"])
    checagens_sem_crescimento = 0
    ultima_tentativa_clicou = True
    yield pagina.content()

    for tentativa in range(1, config.PLAYWRIGHT_MAX_ROLAGENS + 1):
        clicou = _carregar_mais(pagina)
        ultima_tentativa_clicou = clicou
        if not clicou:
            pagina.mouse.wheel(0, 4000)  # fallback: rola a página

        contagem_atual = _esperar_crescer(pagina, contagem_anterior)
        logger.debug(
            "Tentativa %d (%s): %d item(ns) no total até agora.",
            tentativa, "clicou em Veja mais", contagem_atual,
        )

        if contagem_atual > contagem_anterior:
            contagem_anterior = contagem_atual
            checagens_sem_crescimento = 0
            yield pagina.content()
        else:
            checagens_sem_crescimento += 1
            if checagens_sem_crescimento >= config.PLAYWRIGHT_CHECAGENS_ESTAVEIS:
                motivo = (
                    "o botão 'Veja mais' não foi mais encontrado"
                    if not ultima_tentativa_clicou
                    else "a contagem parou de crescer."
                )
                logger.info(
                    "Carregamento encerrado em %d item(ns) após %d tentativa(s): %s.",
                    contagem_atual, tentativa, motivo,
                )
                break
    else:
        logger.warning(
            "Atingiu o limite de %d tentativas sem a contagem estabilizar. "
            "A última tentativa ainda %s e a contagem ainda estava subindo "
            "(%d item(ns) até agora). Pode haver mais resultados: tente aumentar "
            "--max-carregamentos.",
            config.PLAYWRIGHT_MAX_ROLAGENS,
            "clicou no botão 'Veja mais'" if ultima_tentativa_clicou else "não encontrou o botão",
            contagem_anterior
        )


def renderizar_pagina(url: str) -> Iterator[str]:
    """
    Abre a URL em um Chromium headless e cede o HTML do DOM após o
    carregamento inicial e após cada novo carregamento bem-sucedido
    (clique em "Veja mais").
    """

    try:
        with sync_playwright() as pw:
            navegador = pw.chromium.launch(headless=True)
            try:
                pagina = navegador.new_page(user_agent=config.USER_AGENT)
                pagina.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")

                try:
                    pagina.wait_for_function(
                        """
                        (seletor) => {
                            const el = document.querySelector(seletor);
                            return Boolean(el && el.children.length > 0);
                        }
                        """,
                        arg=SELETOR_CONTAINER_RESULTADOS,
                        timeout=config.PLAYWRIGHT_TIMEOUT_MS,
                    )
                except Exception:
                    logger.warning(
                        "Contêiner de resultados não foi preenchido dentro do timeout em %s. "
                        "Pode ser uma página sem resultados, ou uma mudança na estrutura.",
                        url,
                    )
                    yield pagina.content()
                    return

                yield from _iterar_carregamentos(pagina)
            finally:
                navegador.close()
    except Exception as erro:
        logger.error("Falha ao renderizar %s com Playwright: %s", url, erro)
        return
