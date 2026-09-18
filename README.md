# Coleta de resultados de busca do G1 — LGPD (via Playwright)

Rotina de web scraping para coletar os resultados de busca do portal G1
(`https://g1.globo.com/busca/?q=lgpd`), reescrita a partir de um código 
que parou de funcionar.

## Sumário

1. [Diagnóstico](#1-diagnóstico)
2. [Por que Playwright, e por que sem paginação por URL](#2-por-que-playwright-e-por-que-sem-paginação-por-url)
3. [Estrutura do projeto](#3-estrutura-do-projeto)
4. [Instalação](#4-instalação)
5. [Execução](#5-execução)
6. [Sugestões de melhorias futuras](#9-sugestões-de-melhorias-futuras)
7. [Avaliação de qualidade dos dados](#10-avaliação-de-qualidade-dos-dados)
8. [Proposta de uso de LLM](#11-proposta-de-uso-de-llm)

## 1. Diagnóstico

Ao verificar o HTML da página (DevTools), observou-se as seguintes
linhas:

```html
<div class="search-result">
    <div class="container">
        <div class="results__content all-search-results"></div>
    </div>
</div>
```

O contêiner de resultados da busca chega vazio no HTML enviado pelo servidor.
A busca do G1 hoje é um componente React (Module Federation) que busca e
renderiza os resultados inteiramente no navegador, e de forma
progressiva: carrega um primeiro lote e só carrega mais ao clicar no
botão **"Veja mais"**.

## 2. Por que Playwright, e por que sem paginação por URL?

**Por que Playwright**: `requests` só baixa o HTML estático, nunca
executa o JavaScript da página. Como os resultados só existem depois
desse JavaScript rodar, `requests` sozinho não funciona nesse contexto.
Por isso a coleta abre a página em um Chromium headless via Playwright,
espera o JavaScript montar os resultados e só então extrai o HTML final
com BeautifulSoup.

**Por que não há mais `?page=N` na URL**: a versão antiga do G1
usava paginação de verdade por URL. A versão atual é
uma *single-page application*: uma única URL de busca, com os resultados
carregando progressivamente na mesma página, via clique repetido no
botão "Veja mais". Foi verifcado que o parâmetro `page` da URL não 
influencia no resultado da busca.

Por isso o projeto foi refeito assim: `scraper.coletar()` abre a URL de
busca uma única vez e consome um gerador
(`playwright_client.renderizar_pagina`) que:

1. espera o primeiro lote de resultados aparecer;
2. clica em "Veja mais" e verifica se a quantidade de itens no DOM cresceu;
3. repete o passo 2 até a contagem parar de crescer por 2 checagens
   seguidas, ou até um limite de tentativas (`config.PLAYWRIGHT_MAX_ROLAGENS`);
4. retorna (`yield`) o HTML atual a cada carregamento bem-sucedido, para que
   `scraper.py` extraia os itens novos daquele lote.

O campo `lote` na saída indica em qual carregamento aquele item apareceu
pela primeira vez (`1` = resultados iniciais, `2+` = depois de um clique
em "Veja mais").

## 3. Estrutura do projeto

```
g1_scraper_lgpd/
├── main.py                        # CLI de execução da coleta
├── requirements.txt
├── README.md
├── .gitignore
├── g1_scraper/
│   ├── __init__.py
│   ├── config.py                  # URL, seletores HTML, parâmetros do Playwright
│   ├── playwright_client.py       # renderização via Chromium headless
│   ├── parser.py                  # extração dos campos a partir do HTML renderizado
│   ├── scraper.py                 # organização dos lotes
│   └── storage.py                 # exportação para CSV/JSON
├── scripts/
│   ├── avaliar_qualidade.py       # calcula as métricas de qualidade (seção 10)
│   └── gerar_exemplo_ilustrativo.py  # gera o dataset de demonstração (não é dado real do G1)
├── docs/
│   ├── avaliacao_qualidade.md     # metodologia e métricas de qualidade
│   └── proposta_llm.md            # proposta de uso de LLM
├── dados/
│   ├── exemplo_ilustrativo.csv              # dataset de demonstração (ver seção 10)
│   ├── exemplo_ilustrativo_referencia.csv   # referência manual correspondente
│   └── amostra_referencia.exemplo.csv       # modelo vazio para você preencher com dados reais
└── tests/
    ├── test_parser.py
    ├── test_playwright_client.py
    ├── test_scraper.py
    ├── test_storage.py
    └── test_avaliar_qualidade.py
```

## 4. Instalação

Requer Python 3.10+.

```bash
# Crie e ative um ambiente virtual
python3 -m venv .venv

# Linux/macOS
source .venv/bin/activate        

# Windows
.venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
playwright install chromium
```

## 5. Execução

```bash
python3 main.py --termo lgpd --saida g1_lgpd --formato ambos
```

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--termo` | `lgpd` | Termo de busca |
| `--saida` | `g1_resultados` | Nome base dos arquivos gerados (sem extensão) |
| `--formato` | `ambos` | `csv`, `json` ou `ambos` |
| `--max-carregamentos` | `150` | Número máximo de cliques em "Veja mais" |
| `--log` | `INFO` | Use `DEBUG` para ver quantos itens o Playwright reporta a cada tentativa, e qual seletor de card está sendo usado |

Cada resultado sai com os campos: `titulo`, `url`, `resumo`,
`data_publicacao`, `lote` (em qual carregamento apareceu pela primeira
vez) e `coletado_em` (timestamp UTC da coleta).


## 6. Sugestões de melhorias futuras

- Rodar `scripts/avaliar_qualidade.py` automaticamente após cada coleta
  em produção (não só sob demanda), salvando o relatório junto com o
  dataset, para acompanhar a qualidade ao longo do tempo.
- Implementar de fato a proposta de LLM da seção 8. 

## 7. Avaliação de qualidade dos dados

A metodologia completa, as métricas e a justificativa de cada uma estão em
[`docs/avaliacao_qualidade.md`](docs/avaliacao_qualidade.md).

```bash
python scripts/avaliar_qualidade.py 
```

## 8. Proposta de uso de LLM

Proposta técnica completa (com pseudocódigo) em
[`docs/proposta_llm.md`](docs/proposta_LLM.md).
