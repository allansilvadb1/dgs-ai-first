# Code Review — Feedback Handler (Cenário 3, Exercício 3.2 — Desenvolvedor)

**Contexto:** o Copilot gerou um módulo de feedback (`feedback-handler.ts`) que precisava de revisão antes do merge, conforme pedido do Tech Lead. A revisão foi feita em duas etapas independentes — primeiro pelo desenvolvedor, depois pelo Claude — e comparada antes da reescrita.

## Código original (gerado pelo Copilot, simulado)

```typescript
// feedback-handler.ts — gerado pelo Copilot
import { app, HttpRequest, HttpResponseInit } from '@azure/functions';

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const body = await request.json() as any;

  const feedback = {
    queryId: body.queryId,
    rating: body.rating,
    comment: body.comment,
    attendantEmail: body.attendantEmail,
    timestamp: new Date().toISOString()
  };

  console.log('Feedback recebido:', JSON.stringify(feedback));

  const { CosmosClient } = require('@azure/cosmos');
  const client = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
  const database = client.database('novatech');
  const container = database.container('feedbacks');

  await container.items.create(feedback);

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler
});
```

Regras de referência (AGENTS.md): TypeScript strict mode, Zod para validação de input, pino para logging (nunca `console.log`), nunca logar dados pessoais (e-mail, nome), imports estáticos no topo (nunca `require` dinâmico).

---

## Revisão independente — Desenvolvedor

**Bug potencial:**
- Linha 7 (`body = await request.json() as any`): não tem tipo definido para o request nem validação do conteúdo recebido.
- Linha 19 (`require('@azure/cosmos')`): import dinâmico.
- Linha 20 (`new CosmosClient(process.env.COSMOS_CONNECTION_STRING)`): não valida previamente se a variável de ambiente está preenchida com valor válido.

**Problema de segurança:**
- Linha 17 (`console.log('Feedback recebido:', ...)`): log de dados pessoais (`attendantEmail`).
- Linha 4 (função inteira): não há tratamento de exceção para qualquer erro que houver na function.

---

## Revisão independente — Claude

**Violação do AGENTS.md:**
- `body = await request.json() as any` — sem schema Zod validando o input.
- `console.log(...)` — usa `console.log` em vez de pino, **independente do conteúdo logado**.
- `require('@azure/cosmos')` dentro da função — import dinâmico em vez de estático no topo.
- O mesmo `console.log` inclui `attendantEmail` (dado pessoal) — viola "nunca logar dados pessoais".

**Problema de segurança:**
- `attendantEmail` (PII) indo para logs — se centralizados (ex: Application Insights), o dado pessoal vaza para um sistema com retenção/acesso mais amplo do que deveria.
- Zero validação antes de persistir no Cosmos — `rating` sem range, `comment` sem tamanho máximo, `queryId` não confirmado.

**Bug potencial:**
- `require` dinâmico não é só estilo: o `package.json` declara `"type": "module"`. Em ESM nativo do Node, `require` não existe sem `createRequire` — a function provavelmente quebra em runtime (`ReferenceError: require is not defined`).
- Sem `try/catch` — qualquer falha (Cosmos indisponível, env var ausente) derruba a function sem resposta controlada.
- `COSMOS_CONNECTION_STRING` não é validada antes de instanciar o client.
- (Secundário) `CosmosClient` é recriado a cada invocação em vez de reaproveitado no escopo do módulo.

---

## Comparação

| Achado                                                               | Desenvolvedor                  | Claude                                                               |
| -------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------- |
| `as any` / falta de validação de input                               | ✅ (bug potencial)              | ✅ (também classificado como violação do AGENTS.md — Zod obrigatório) |
| `require` dinâmico                                                   | ✅ (bug potencial)              | ✅ (violação do AGENTS.md **e** bug real de runtime em projeto ESM)   |
| Falta de validação da env var                                        | ✅                              | ✅                                                                    |
| `attendantEmail` logado                                              | ✅ (segurança)                  | ✅ (segurança **e** violação do AGENTS.md)                            |
| Falta de `try/catch`                                                 | ✅                              | ✅                                                                    |
| `console.log` em vez de pino (como problema em si, além do conteúdo) | Não identificado separadamente | ✅                                                                    |
| `CosmosClient` recriado por request                                  | Não identificado               | ✅ (secundário)                                                       |

**Convergência:** ambas as revisões identificaram os mesmos riscos centrais — dado pessoal em log, import dinâmico, falta de validação e de tratamento de erro.

**Divergência:** a revisão do desenvolvedor tratou `console.log` apenas pelo conteúdo (dado pessoal), sem marcar o uso da ferramenta em si (vs. pino) como violação independente. Também classificou `as any` e `require` dinâmico só como "bug potencial", enquanto o Claude aplicou dupla classificação (bug + violação nomeada do AGENTS.md), já que ambas as regras são explícitas no documento. A revisão do Claude também elevou a severidade do `require` dinâmico ao identificar que é um bug real de runtime (projeto é ESM), não apenas uma questão de convenção.

---

## Código reescrito

Arquivos finais no repositório:
- [`src/functions/feedback/handler.ts`](../src/functions/feedback/handler.ts) — imports estáticos, validação via Zod, logging via pino sem PII, `try/catch` no Cosmos, guard de `COSMOS_CONNECTION_STRING` ausente.
- [`src/functions/feedback/validator.ts`](../src/functions/feedback/validator.ts) — schema Zod do payload de feedback.
- [`src/shared/logger.ts`](../src/shared/logger.ts) — instância pino compartilhada.

## Pendência residual

- `pino-pretty` (usado no transport de dev do `logger.ts` fora de produção) não foi instalado — não bloqueia os critérios do exercício, mas impede o logging formatado em ambiente local. Rodar `npm install pino-pretty` quando for testar a function localmente.
