# Avaliação de qualidade dos dados coletados

## As sete dimensões e como cada uma é medida

| Dimensão | Definição usada aqui | Como é medida |
|---|---|---|
| **Completude** | Proporção de campos preenchidos (não nulos/vazios) sobre o total esperado | `% de valores não vazios por coluna`, calculado sobre o dataset inteiro |
| **Unicidade** | Ausência de registros duplicados | `1 - (duplicatas encontradas / total de registros)`, comparando a URL normalizada de cada linha |
| **Consistência** | Uniformidade de formato entre os registros | Checagem de schema (todas as colunas esperadas presentes, em toda linha), formato de `coletado_em` (ISO 8601) e de `lote` (inteiro positivo) | 
| **Rastreabilidade** | Capacidade de voltar à fonte original de cada registro | `% de linhas com url e coletado_em preenchidos ao mesmo tempo` | 
| **Atualidade** | Os dados refletem o estado mais recente da fonte | Diferença entre `coletado_em` e o momento da execução do script de avaliação (deve ser recente); e verificação de que `data_publicacao`, quando presente, não é uma data futura absurda | Não — automático (mas o significado de "recente" depende de quando a avaliação é rodada) |
| **Precisão** | O formato/estrutura de cada campo está correto (ex.: URL é uma URL válida, data está num formato reconhecível) | Validação de formato por regex/parsing (URL começa com `http`, data bate com um padrão de data conhecido) | 
| **Acurácia** | O conteúdo de cada campo está correto, comparado à fonte real | Comparação campo a campo contra uma amostra de referência construída manualmente (olhando o navegador) |

## Amostra de referência

Uma pequena amostra de referência foi construída manualmente em `dados/amostra_referencia.csv`. O arquivo foi preenchido a partir da observação dos reaultados da busca na página
`https://g1.globo.com/busca/?q=lgpd`.

O script casa cada linha da referência com a linha correspondente do
dataset coletado e calcula a taxa de acerto por campo.

## Métricas de acurácia: correspondência exata vs. aproximada

Para `titulo` e `resumo`, uma comparação de igualdade exata (`==`) é frágil
demais, pequenas diferenças de espaçamento, aspas curvas vs. retas, ou
truncamento do resumo pelo próprio G1 gerariam falsos negativos. Por isso
o script usa duas métricas complementares:

- **Correspondência exata**: útil para campos que devem ser idênticos
  caractere a caractere (URL, depois de normalizada).
- **Similaridade textual** (`difflib.SequenceMatcher`, de 0 a 1): usada
  para título e resumo, com um limiar de aceitação configurável (padrão:
  `0.85`).
