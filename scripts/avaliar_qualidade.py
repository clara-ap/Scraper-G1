"""
Calcula métricas de qualidade sobre um dataset coletado pelo scraper, e
compara contra uma amostra de referência construída manualmente, para 
medir acurácia.

Uso:
    python scripts/avaliar_qualidade.py --dados dados/g1_resultados.csv
    python scripts/avaliar_qualidade.py --dados dados/dataset_lgpd.csv \\
        --referencia dados/amostra_referencia.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

CAMPOS_ESPERADOS = ["titulo", "url", "resumo", "data_publicacao", "lote", "coletado_em"]
LIMIAR_SIMILARIDADE_TEXTO = 0.85

def _ler_csv(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def _normalizar_url(url: str) -> str:
    return re.sub(r"[?#].*$", "", url or "").rstrip("/")


def _similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


def avaliar_completude(dados: list[dict]) -> dict:
    """ % de valores não vazios por coluna, sobre o total de registros. """
    if not dados:
        return {campo: 0.0 for campo in CAMPOS_ESPERADOS}
    total = len(dados)
    return {
        campo: round(sum(1 for linha in dados if (linha.get(campo) or "").strip()) / total * 100, 1)
        for campo in CAMPOS_ESPERADOS
    }


def avaliar_unicidade(dados: list[dict]) -> dict:
    """ Proporção de registros com URL normalizada única. """
    urls = [_normalizar_url(linha.get("url", "")) for linha in dados if linha.get("url")]
    total = len(urls)
    unicas = len(set(urls))
    duplicatas = total - unicas
    return {
        "total_com_url": total,
        "urls_unicas": unicas,
        "duplicatas_encontradas": duplicatas,
        "taxa_unicidade_pct": round(unicas / total * 100, 1) if total else 0.0,
    }


def avaliar_consistencia(dados: list[dict]) -> dict:
    """ Schema uniforme, formato de coletado_em (ISO 8601) e lote (inteiro positivo). """
    if not dados:
        return {"schema_ok": True, "timestamps_validos_pct": 0.0, "lotes_validos_pct": 0.0}

    colunas_por_linha = {tuple(sorted(linha.keys())) for linha in dados}
    schema_ok = len(colunas_por_linha) == 1 and set(next(iter(colunas_por_linha))) >= set(CAMPOS_ESPERADOS)

    def _timestamp_valido(valor: str) -> bool:
        try:
            datetime.fromisoformat(valor)
            return True
        except (ValueError, TypeError):
            return False

    def _lote_valido(valor: str) -> bool:
        try:
            return int(valor) > 0
        except (ValueError, TypeError):
            return False

    total = len(dados)
    return {
        "schema_ok": schema_ok,
        "timestamps_validos_pct": round(
            sum(1 for linha in dados if _timestamp_valido(linha.get("coletado_em", ""))) / total * 100, 1
        ),
        "lotes_validos_pct": round(
            sum(1 for linha in dados if _lote_valido(linha.get("lote", ""))) / total * 100, 1
        ),
    }


def avaliar_rastreabilidade(dados: list[dict]) -> dict:
    """ % de linhas com url e coletado_em preenchidos ao mesmo tempo. """
    if not dados:
        return {"taxa_rastreabilidade_pct": 0.0}
    total = len(dados)
    rastreaveis = sum(
        1 for linha in dados if (linha.get("url") or "").strip() and (linha.get("coletado_em") or "").strip()
    )
    return {"taxa_rastreabilidade_pct": round(rastreaveis / total * 100, 1)}


def avaliar_precisao_formato(dados: list[dict]) -> dict:
    """ Os campos preenchidos têm um formato válido. """
    urls_validas = 0
    urls_preenchidas = 0
    for linha in dados:
        url = (linha.get("url") or "").strip()
        if url:
            urls_preenchidas += 1
            partes = urlparse(url)
            if partes.scheme in ("http", "https") and partes.netloc:
                urls_validas += 1
    return {
        "urls_formato_valido_pct": round(urls_validas / urls_preenchidas * 100, 1) if urls_preenchidas else 0.0,
    }


def avaliar_atualidade(dados: list[dict], agora: datetime | None = None) -> dict:
    """ Quão recente é coletado_em em relação ao momento desta avaliação. """
    agora = agora or datetime.now(timezone.utc)
    diferencas_horas = []
    for linha in dados:
        valor = linha.get("coletado_em", "")
        try:
            momento = datetime.fromisoformat(valor)
        except (ValueError, TypeError):
            continue
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        diferencas_horas.append((agora - momento).total_seconds() / 3600)

    if not diferencas_horas:
        return {"idade_media_horas": None, "idade_maxima_horas": None}
    return {
        "idade_media_horas": round(sum(diferencas_horas) / len(diferencas_horas), 2),
        "idade_maxima_horas": round(max(diferencas_horas), 2),
    }


def avaliar_acuracia(dados: list[dict], referencia: list[dict]) -> dict:
    """
    Compara cada linha da referência com a linha correspondente do dataset
    coletado.
    """
    dados_por_url = {_normalizar_url(linha.get("url", "")): linha for linha in dados}

    encontrados = 0
    titulo_exato = 0
    titulo_similar = 0
    resumo_similar = 0
    data_exata = 0

    for ref in referencia:
        chave = _normalizar_url(ref.get("url", ""))
        correspondente = dados_por_url.get(chave)
        if not correspondente:
            continue
        encontrados += 1

        if (correspondente.get("titulo") or "") == (ref.get("titulo_esperado") or ""):
            titulo_exato += 1
        if _similaridade(correspondente.get("titulo", ""), ref.get("titulo_esperado", "")) >= LIMIAR_SIMILARIDADE_TEXTO:
            titulo_similar += 1
        if _similaridade(correspondente.get("resumo", ""), ref.get("resumo_esperado", "")) >= LIMIAR_SIMILARIDADE_TEXTO:
            resumo_similar += 1
        if (correspondente.get("data_publicacao") or "") == (ref.get("data_esperada") or ""):
            data_exata += 1

    total_referencia = len(referencia)
    return {
        "total_amostra_referencia": total_referencia,
        "encontrados_no_dataset_pct": round(encontrados / total_referencia * 100, 1) if total_referencia else 0.0,
        "titulo_exato_pct": round(titulo_exato / encontrados * 100, 1) if encontrados else 0.0,
        "titulo_similar_pct": round(titulo_similar / encontrados * 100, 1) if encontrados else 0.0,
        "resumo_similar_pct": round(resumo_similar / encontrados * 100, 1) if encontrados else 0.0,
        "data_exata_pct": round(data_exata / encontrados * 100, 1) if encontrados else 0.0,
    }


def gerar_relatorio(caminho_dados: str, caminho_referencia: str | None) -> str:
    dados = _ler_csv(caminho_dados)

    linhas = [
        f"Registros no dataset: {len(dados)}",
        "",
        "== Completude ==",
        *(f"  {campo}: {valor}%" for campo, valor in avaliar_completude(dados).items()),
        "",
        "== Unicidade ==",
        *(f"  {chave}: {valor}" for chave, valor in avaliar_unicidade(dados).items()),
        "",
        "== Consistência ==",
        *(f"  {chave}: {valor}" for chave, valor in avaliar_consistencia(dados).items()),
        "",
        "== Rastreabilidade ==",
        *(f"  {chave}: {valor}" for chave, valor in avaliar_rastreabilidade(dados).items()),
        "",
        "== Precisão (formato) ==",
        *(f"  {chave}: {valor}" for chave, valor in avaliar_precisao_formato(dados).items()),
        "",
        "== Atualidade ==",
        *(f"  {chave}: {valor}" for chave, valor in avaliar_atualidade(dados).items()),
    ]

    if caminho_referencia:
        referencia = _ler_csv(caminho_referencia)
        linhas += [
            "",
            "== Acurácia ==",
            *(f"  {chave}: {valor}" for chave, valor in avaliar_acuracia(dados, referencia).items()),
        ]
    else:
        linhas += [
            "",
            "== Acurácia ==",
            "  (não avaliada, tente novamente)",
        ]

    return "\n".join(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", default="dados/g1_resultados.csv",
                        help="CSV gerado pelo scraper.")
    parser.add_argument("--referencia", default="dados/amostra_referencia.csv",
                        help="CSV com a amostra de referência construída manualmente.")
    args = parser.parse_args()

    if not Path(args.dados).exists():
        raise SystemExit(f"Arquivo não encontrado: {args.dados}")

    print(gerar_relatorio(args.dados, args.referencia))


if __name__ == "__main__":
    main()
