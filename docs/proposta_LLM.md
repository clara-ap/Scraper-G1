# Proposta de uso de LLM 

Este documento descreve uma proposta técnica de como um modelo de linguagem (LLM) 
pode agregar ao projeto.

## Diagnóstico de quebra de seletor

**Quando roda**: sempre que `scraper.coletar()` terminar com poucos ou zero
resultados.

**O que é dado ao modelo**:
- Um trecho do HTML real e atual da página, truncado para as primeiras N ocorrências de elementos candidatos a "card".
- A lista atual de seletores em `config.py` (`SELECTORS`).
- Os logs de execução mais recentes (`Seletor de card em uso: ... (N
  encontrados)`, avisos de `Nenhum card encontrado`, etc.).

**O que se pede ao modelo**: comparar a estrutura do HTML atual com os
seletores configurados e sugerir **um seletor CSS candidato** para cada
campo que parece ter parado de funcionar (`card`, `titulo`, `resumo`,
`data`, `link`).

**Formato de saída exigido do modelo**: um JSON:

```json
{
  "card": {"seletor_sugerido": "li.article-card"},
  "titulo": {"seletor_sugerido": ".article-card__headline"},
}
```

**Como a resposta é validada antes de qualquer coisa ser incorporada**:

1. **Validação sintática**: o seletor sugerido precisa ser um seletor CSS
   sintaticamente válido. Checado em código.
2. **Validação de contagem**: o seletor sugerido, aplicado ao mesmo HTML,
   precisa encontrar uma contagem de elementos compatível com o
   esperado (por exemplo, para `card`, mais de 1 elemento, para `titulo`
   dentro de um card, exatamente 0 ou 1). Um seletor que faz sentido
   sintaticamente mas devolve 0 elementos, ou um número absurdo, é
   rejeitado automaticamente.
3. **Revisão final**: mesmo passando pelas checagens acima, a
   mudança em `config.py` é proposta como um *diff* para revisão humana
   (pull request), nunca aplicada automaticamente em produção. A LLM
   acelera o diagnóstico, mas não tem permissão de escrita
   direta no repositório.

## Exemplo de pseudocódigo

```python
def diagnosticar_seletor_quebrado(html_recente: str, config_atual: dict) -> dict | None:
    """
    Usa uma LLM para sugerir um novo seletor de card, validando a
    resposta antes de aceitar qualquer coisa.
    """
    prompt = montar_prompt_diagnostico(html_recente, config_atual)

    resposta_bruta = chamar_llm(
        prompt,
        response_format="json",  
        temperature=0,
    )

    try:
        sugestao = json.loads(resposta_bruta)
    except json.JSONDecodeError:
        logger.warning("LLM devolveu JSON inválido; descartando sugestão.")
        return None

    seletor_sugerido = sugestao.get("card", {}).get("seletor_sugerido")
    if not seletor_sugerido:
        return None

    # Camada 1: sintaxe válida
    soup = BeautifulSoup(html_recente, "html.parser")
    try:
        elementos = soup.select(seletor_sugerido)
    except Exception:
        logger.warning("Seletor sugerido pela LLM é sintaticamente inválido.")
        return None

    # Camada 2: contagem plausível 
    if not (1 < len(elementos) < 200):
        logger.warning(
            "Seletor sugerido encontrou %d elemento(s), fora da faixa plausível.",
            len(elementos),
        )
        return None

    return {"seletor": seletor_sugerido}
```
