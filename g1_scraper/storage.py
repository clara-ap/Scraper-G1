""" Salva os resultados em CSV e/ou JSON. """

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Iterable

from . import config

logger = logging.getLogger(__name__)


def salvar_csv(dados: Iterable[dict], caminho: str | Path) -> None:
    """ Salva os resultados em CSV, sempre com cabeçalho e encoding utf-8. """
    caminho = Path(caminho)
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=config.CAMPOS_SAIDA)
        escritor.writeheader()
        for linha in dados:
            escritor.writerow({chave: linha.get(chave, "") for chave in config.CAMPOS_SAIDA})
    logger.info("CSV salvo em %s", caminho)


def salvar_json(dados: Iterable[dict], caminho: str | Path) -> None:
    """ Salva os resultados em JSON, preservando acentuação. """
    caminho = Path(caminho)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(list(dados), arquivo, ensure_ascii=False, indent=2)
    logger.info("JSON salvo em %s", caminho)
