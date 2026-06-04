# Análise das Respostas (V1)
Pergunta 1 — Carga perigosa

- Resultado: Correto e completo. Identificou a exceção, não inventou procedimento alternativo, escalou para supervisor como manda a regra 3.
Guardrails: todos respeitados.

Pergunta 2 — SLA Gold

- Resultado: Correto. 24h de resolução, fonte citada.
- Problema menor: adicionou um "Lembrete" sobre registrar chamado corretamente — isso não estava nos chunks. O modelo está sendo "útil demais", acrescentando conselho que não foi pedido e que pode confundir o atendente.

Pergunta 3 — Frete Manaus

- Resultado: Correto e honesto. Identificou Região Norte, aplicou multiplicador 1.8, e admitiu que o valor base não está na documentação.
- Guardrail 2 funcionou perfeitamente: não inventou o valor base.
O que o v2 precisa corrigir

Só um problema real: o modelo está adicionando conselhos não solicitados que não vêm dos chunks (o "Lembrete" da pergunta 2). Em produção, isso é perigoso — o atendente pode confiar em algo que o assistente inventou como boa prática.

Adicione esta regra ao prompt:

```
5. Não adicione conselhos, lembretes ou sugestões além da resposta direta à 
   pergunta. Se a informação não está nos chunks, não mencione.
System Prompt v2 — completo para colar
```

# Análise das Respostas (V2)


Comparação v1 vs v2
Pergunta 2 — o teste da correção

|     | v1  | v2  |
| --- | --- | --- |  |---------- |
| Resposta core             | SLA correto ✅ | SLA correto ✅ |
| "Lembrete" não solicitado | Presente ❌    | Ausente ✅     |

A regra 5 funcionou. O modelo parou de inventar conselhos.

Perguntas 1 e 3 — os alertas que sobraram são justificados

Os `⚠️ Atenção` que ainda aparecem não são o problema que corrigimos — eles surgem porque a documentação genuinamente tem lacunas (carga perigosa não tem procedimento alternativo; valor base não está nos chunks). O modelo está aplicando a regra 3 corretamente nesses casos.

---

Neste ponto Allan observou o número de tokens do prompt "Identidade + Regras + Prioridade + Formato" é maior em portugues do que em ingles. Após pesquisa observou que não está totalmente atrelado ao idioma mas sim a verbosidade. O novo prompt foi gerado focando em instruir, sem redundancia e com menos verbosidade.

# Analise das Respostas (v3)

v3 está correto e mais enxuto em todos os pontos
|                | v2                               | v3                                                             |
| -------------- | -------------------------------- | -------------------------------------------------------------- |
| Carga perigosa | Correta + alerta de escalada     | Correta, sem alerta                                            |
| SLA Gold       | Resposta + resposta inicial (2h) | Só resolução (24h) — respondeu exatamente o que foi perguntado |
| Frete Manaus   | Correto + alerta formatado       | Correto, mais direto                                           |

Um trade-off que vale documentar
Na Pergunta 1, o v2 recomendava escalar ao supervisor. O v3 não faz isso — apenas informa que não pode devolver.

Isso aconteceu porque a regra comprimida (Alerta apenas se documentação for incompleta) foi interpretada corretamente: a documentação está completa (proíbe a devolução), então não há gap. Mas na prática, o atendente ainda precisa saber o que fazer quando o cliente insiste.

Isso não é falha do prompt v3 — é uma decisão de produto. Para o exercício, vale mencionar:

Em resumo: a compressão do prompt gerou respostas mais precisas mas reduziu a orientação ao atendente em casos de exceção. Em produção, esse trade-off seria resolvido com uma regra explícita: Quando a resposta for uma proibição sem procedimento alternativo, sempre recomendar escalar ao supervisor.

---

Resumo da evolução dos 3 prompts
| Versão | Problema                                | Correção                             |
| ------ | --------------------------------------- | ------------------------------------ |
| v1     | Conselhos não solicitados (Q2)          | Adicionou regra 5                    |
| v2     | Verbosidade (~382 tokens)               | Comprimiu para ~180 tokens           |
| v3     | Trade-off: menos orientação em exceções | A documentar como decisão de produto |
