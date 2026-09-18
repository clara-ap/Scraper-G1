from __future__ import annotations

import argparse
import logging

from g1_scraper import config
from g1_scraper.scraper import coletar
from g1_scraper.storage import salvar_csv, salvar_json


def configurar_logging(nivel: str) -> None:
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=("Coleta resultados de busca do G1."))
    parser.add_argument("--termo", default=config.TERMO_BUSCA_PADRAO, help="Termo de busca")
    parser.add_argument("--saida", default="dados/g1_resultados", help="Nome base do arquivo de saída (sem extensão)")
    parser.add_argument("--formato", choices=["csv", "json", "ambos"], default="ambos", help="Formato de saída")
    parser.add_argument("--max-carregamentos", type=int, default=config.PLAYWRIGHT_MAX_ROLAGENS,
        help="Número máximo de cliques em 'Veja mais' (cada clique tende a trazer mais resultados)")
    parser.add_argument("--log", default="INFO", help="Nível de log (DEBUG, INFO, WARNING...)")
    args = parser.parse_args()

    configurar_logging(args.log)
    logger = logging.getLogger(__name__)

    config.PLAYWRIGHT_MAX_ROLAGENS = args.max_carregamentos

    resultados = coletar(termo_busca=args.termo)

    if not resultados:
        logger.error(
            "Nenhum resultado coletado. Rode com --log DEBUG para ver quantos itens o "
            "Playwright carregou por lote e se algum seletor em g1_scraper/config.py "
            "(SELECTORS) está batendo com o HTML renderizado."
        )

    if args.formato in ("csv", "ambos"):
        salvar_csv(resultados, f"{args.saida}.csv")
    if args.formato in ("json", "ambos"):
        salvar_json(resultados, f"{args.saida}.json")

    print(f"Coleta finalizada: {len(resultados)} resultado(s) único(s) salvos em '{args.saida}.*'.")


if __name__ == "__main__":
    main()
