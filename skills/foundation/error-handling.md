# SKILL: error-handling

> **Foundation Level**  
> Padrão obrigatório de tratamento de erros do projeto NovaTech Assistant.  
> Toda camada que gera código (handler, service, pipeline) **DEVE** seguir este padrão.

---

## Context

### Quando usar esta skill

- **Criando um novo handler HTTP** em `src/functions/*/handler.ts`
- **Adicionando validação** com Zod em função pública
- **Implementando um serviço** em `src/services/*.ts` que pode falhar
- **Tratando exceções** de chamadas externas (Azure Search, LLM, base de dados)
- **Estruturando logs** em qualquer arquivo TypeScript do projeto

### Por que existe

O projeto executa em produção (Azure Functions) onde:
1. **Erros genéricos** (string message de catch) não permitem rastreamento.
2. **console.log** não integra com observabilidade (Datadog, Graylog).
3. **Handlers sem try/catch** deixam exceptions não tratadas e criam 500s genéricos.
4. **LLMs geram código** com console.log e erros soltos → é necessário ser **muito prescritivo**.

### Escopo

Cobre:
- ✅ Definição da classe `AppError`
- ✅ Logging estruturado com `pino`
- ✅ Tratamento de exceções em handlers e services
- ✅ Mapeamento de erros para respostas HTTP
- ✅ Integração com Azure Functions v4 (InvocationContext)

Não cobre:
- ❌ Observabilidade remota (Datadog) — vem de `config.ts`
- ❌ Recuperação automática / retry — vem de `azure-functions-endpoint` skill
- ❌ Padrão de request/response completo — vem de `azure-functions-endpoint` skill

---

## Prescriptive Rules

### DEVE

1. **Toda exceção não esperada recebe `AppError`**
   - Exceções primitivas (Error, TypeError, ReferenceError) **não** devem escapar handlers.
   - Contexto: handler → service → catch(e) → lance AppError ou deixe propagar se já é AppError.

2. **Todo log estruturado usa `pino`**
   - Nunca use `console.log`, `console.error`, `console.warn`, `console.debug`.
   - Logs devem passar pelo `logger` injetado via construtor ou contexto.

3. **`AppError` sempre contém `code` e `httpStatus`**
   - `code`: identificador de erro (ex: "VALIDATION_ERROR", "SEARCH_NOT_FOUND", "LLM_TIMEOUT").
   - `httpStatus`: status HTTP correspondente (ex: 400, 404, 503).
   - Exemplo: `new AppError("VALIDATION_ERROR", 400, "Campo obrigatório falta: query")`.

4. **Handlers HTTP nunca trata AppError explicitamente**
   - Deixa a exceção subir para o `InvocationContext` do Azure Functions v4.
   - O middleware global (`CustomizedResponseEntityExceptionHandler` ou equivalente) trata automaticamente.

5. **Serviços e pipeline **podem** tratar AppError internamente**
   - Se a falha é recuperável (ex: retry após timeout), trate e lance AppError customizado.
   - Se não é recuperável, deixe subir para o handler.

6. **Logs contêm contexto**
   - Nunca log vazio como `logger.info("buscando")`.
   - Sempre inclua dados estruturados: `logger.info({ query: q, chunks: n }, "busca executada")`.
   - Dados sensíveis (CPF, email, senha, token) **NUNCA** em log — use mascaramento ou omita.

7. **Erros em cadeia preservam stack trace**
   - Ao criar AppError a partir de outra exceção, use `cause` ou `Error.captureStackTrace` para rastreabilidade.

### NÃO DEVE

1. ❌ **Não lance string pura em `throw`**
   ```typescript
   // RUIM
   throw "Erro ao buscar documento";
   ```

2. ❌ **Não use `console.log`, `console.error` ou similar**
   ```typescript
   // RUIM
   console.log("Documento encontrado:", doc);
   console.error("Falha na busca:", error.message);
   ```

3. ❌ **Não ignore exceções com `.catch(() => {})`**
   ```typescript
   // RUIM
   searchClient.search(query).catch(() => {});
   ```

4. ❌ **Não crie AppError sem httpStatus**
   ```typescript
   // RUIM
   throw new AppError("TIMEOUT", null, "Chamada demorou muito");
   ```

5. ❌ **Não misture try/catch genérico com lógica específica**
   ```typescript
   // RUIM
   try {
     const result = await service.execute();
     logger.info(result); // OK, mas misturado
   } catch (e) {
     if (e instanceof TimeoutError) { /* ... */ }
     else if (e instanceof ValidationError) { /* ... */ }
     else logger.error(e); // Muito genérico
   }
   ```

6. ❌ **Não registre dados sensíveis sem mascaramento**
   ```typescript
   // RUIM
   logger.info({ email: user.email, cpf: user.cpf }, "usuário criado");
   ```

7. ❌ **Não capture apenas a mensagem de erro e perca o stack**
   ```typescript
   // RUIM
   catch (e) {
     throw new AppError("UNKNOWN", 500, e.message); // Perdeu o stack
   }
   ```

---

## Code Examples: DO ✅ / DON'T ❌

### Example 1: Validação com Zod em Handler

#### ✅ DO

```typescript
// src/functions/query/handler.ts
import { HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { z } from "zod";
import { AppError } from "@/shared/errors";
import { logger as createLogger } from "@/shared/logger";

const QueryInputSchema = z.object({
  query: z.string().min(1, "query is required").max(500),
  userId: z.string().uuid("userId must be valid UUID").optional(),
});

type QueryInput = z.infer<typeof QueryInputSchema>;

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  const logger = createLogger(context);
  
  try {
    logger.info({ path: request.url }, "handler invoked");

    // Validar input
    let input: QueryInput;
    try {
      input = QueryInputSchema.parse(await request.json());
    } catch (validationError) {
      if (validationError instanceof z.ZodError) {
        const message = validationError.errors.map((e) => e.message).join("; ");
        throw new AppError("VALIDATION_ERROR", 400, message);
      }
      throw validationError; // Não é Zod → deixa subir
    }

    logger.info({ query: input.query }, "input validated");

    // Chamar service (assume que QueryService.execute lança AppError se falhar)
    const result = await queryService.execute(input, context);

    logger.info({ resultId: result.id }, "query executed successfully");

    return {
      status: 200,
      body: JSON.stringify(result),
      headers: { "Content-Type": "application/json" },
    };
  } catch (error) {
    // Deixar a exceção subir — middleware global trata
    logger.error({ error, stack: error instanceof Error ? error.stack : undefined }, "handler failed");
    throw error;
  }
}
```

#### ❌ DON'T

```typescript
// src/functions/query/handler.ts
export async function queryHandler(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
  console.log("Handler invoked"); // ❌ console.log

  const input = await request.json();
  
  if (!input.query) {
    throw "Missing query"; // ❌ Lança string
  }

  try {
    const result = await queryService.execute(input); // Sem contexto
  } catch (e) {
    console.error(e); // ❌ console.error
    return { status: 500, body: "Error" }; // ❌ Trata na mão (deveria deixar subir)
  }
}
```

---

### Example 2: Service com Chamada Externa (Azure AI Search)

#### ✅ DO

```typescript
// src/services/search.ts
import { SearchClient } from "@azure/search-documents";
import { AppError } from "@/shared/errors";
import { pino } from "pino";

export class SearchService {
  constructor(
    private searchClient: SearchClient<any>,
    private logger: pino.Logger
  ) {}

  async retrieveChunks(query: string, topK: number = 5): Promise<any[]> {
    this.logger.info({ query, topK }, "starting retrieval");

    try {
      const startTime = Date.now();
      const results = await this.searchClient.search(query, {
        top: topK,
        scoringStatistics: "global",
      });

      const chunks = results.results.map((r) => ({
        id: r.document.id,
        content: r.document.content,
        score: r.score,
        sourceDocument: r.document.sourceDocument,
      }));

      this.logger.info(
        { 
          query: query.substring(0, 50), // Log truncado
          count: chunks.length, 
          durationMs: Date.now() - startTime 
        },
        "retrieval completed"
      );

      return chunks;
    } catch (error) {
      // Captura erro específico de Search
      if (error instanceof Error && error.message.includes("timeout")) {
        throw new AppError(
          "SEARCH_TIMEOUT",
          503,
          `Search service did not respond within timeout: ${error.message}`
        );
      }

      // Erro desconhecido
      throw new AppError(
        "SEARCH_ERROR",
        503,
        `Failed to retrieve chunks: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }
}
```

#### ❌ DON'T

```typescript
// src/services/search.ts
export class SearchService {
  async retrieveChunks(query: string, topK: number = 5): Promise<any[]> {
    console.log("Searching for:", query); // ❌ console.log

    const results = await this.searchClient.search(query, { top: topK }); // Sem tratamento

    return results.results.map((r) => ({
      ...r.document,
      query, // ❌ Repete input
      timestamp: new Date().toISOString(), // ❌ Log sem estrutura
    }));
  }
}
```

---

### Example 3: Pipeline com Múltiplas Etapas

#### ✅ DO

```typescript
// src/pipeline/query-pipeline.ts
import { AppError } from "@/shared/errors";
import { pino } from "pino";

export class QueryPipeline {
  constructor(
    private searchService: SearchService,
    private completionService: CompletionService,
    private logger: pino.Logger
  ) {}

  async execute(
    query: string,
    userId?: string
  ): Promise<{ answer: string; sources: any[] }> {
    const pipelineId = crypto.randomUUID();
    this.logger.info(
      { pipelineId, query: query.substring(0, 50), userId },
      "pipeline started"
    );

    try {
      // Step 1: Retrieve
      this.logger.debug({ pipelineId }, "step 1: retrieve");
      const chunks = await this.searchService.retrieveChunks(query);

      if (chunks.length === 0) {
        throw new AppError(
          "NO_DOCUMENTS_FOUND",
          404,
          "No documents matched the query"
        );
      }

      this.logger.info(
        { pipelineId, chunksRetrieved: chunks.length },
        "retrieval successful"
      );

      // Step 2: Build prompt
      this.logger.debug({ pipelineId }, "step 2: build prompt");
      const prompt = this.buildPrompt(query, chunks);

      // Step 3: Call LLM
      this.logger.debug({ pipelineId }, "step 3: call LLM");
      const answer = await this.completionService.complete(prompt);

      this.logger.info(
        { pipelineId, answerLength: answer.length },
        "pipeline completed"
      );

      return {
        answer,
        sources: chunks.map((c) => ({ id: c.id, document: c.sourceDocument })),
      };
    } catch (error) {
      // AppError já vem com httpStatus → deixa subir
      if (error instanceof AppError) {
        this.logger.warn(
          { pipelineId, code: error.code },
          `pipeline failed at: ${error.message}`
        );
        throw error;
      }

      // Erro inesperado
      this.logger.error(
        { pipelineId, error: error instanceof Error ? error.message : String(error) },
        "pipeline failed with unexpected error"
      );
      throw new AppError("PIPELINE_ERROR", 500, "Internal pipeline error");
    }
  }

  private buildPrompt(query: string, chunks: any[]): string {
    // Lógica de prompt
    return `Context: ${chunks.map((c) => c.content).join("\n")}\n\nQuestion: ${query}`;
  }
}
```

#### ❌ DON'T

```typescript
// src/pipeline/query-pipeline.ts
export class QueryPipeline {
  async execute(query: string): Promise<any> {
    const chunks = await this.searchService.retrieveChunks(query)
      .catch((e) => {
        console.error("Search failed", e); // ❌ console.error + ignora erro
        return [];
      });

    if (chunks.length === 0) {
      // ❌ Deixa passar silenciosamente
    }

    const answer = await this.completionService.complete(
      `Context: ${chunks}\n\nQuestion: ${query}`
    ); // ❌ Sem try/catch

    return { answer }; // ❌ Sem estrutura
  }
}
```

---

### Example 4: Logger Injection Pattern

#### ✅ DO

```typescript
// src/shared/logger.ts
import { pino } from "pino";
import { InvocationContext } from "@azure/functions";

export function createLogger(context?: InvocationContext): pino.Logger {
  // Se houver contexto (Azure Functions), integrar com correlação
  const traceId = context?.traceContext?.traceparent?.split("-")[1] || "local";

  return pino(
    {
      level: process.env.LOG_LEVEL || "info",
      base: {
        traceId, // Correlação para Datadog
        service: "novatech-assistant",
      },
    },
    pino.transport({
      target: "pino/file",
      options: { destination: 1 }, // stdout
    })
  );
}

// Em um handler
import { logger as createLogger } from "@/shared/logger";

export async function handler(request: HttpRequest, context: InvocationContext) {
  const logger = createLogger(context);
  logger.info("Request received"); // Carrega traceId automaticamente
}
```

#### ❌ DON'T

```typescript
// ❌ Criar logger global sem contexto
export const logger = pino();

// ❌ Logger como singleton sem injeção
class MyService {
  log() {
    logger.info("algo"); // Sem correlação de request
  }
}
```

---

## Common AI-Generated Anti-Patterns

Estes são erros que LLMs (Copilot, Claude) frequentemente geram **sem explicit guidance**:

### Anti-Pattern 1: Try/Catch que Trata e Ignora

```typescript
// ❌ ANTI-PATTERN: LLM gera isso frequentemente
try {
  await importantOperation();
} catch (e) {
  // Trata silenciosamente
}
```

**Por quê é ruim:** Erros desaparecem; debugging é impossível.

**Prescrição:** Sempre lance AppError ou re-lance:
```typescript
try {
  await importantOperation();
} catch (e) {
  throw new AppError("OPERATION_FAILED", 500, String(e));
}
```

---

### Anti-Pattern 2: Logging de Objeto Inteiro

```typescript
// ❌ ANTI-PATTERN
const result = { userId: 123, email: "user@example.com", cpf: "12345678900", data: { ... } };
logger.info(result); // Log completo — sensível exposto
```

**Por quê é ruim:** Dados sensíveis em logs; incide em compliance (LGPD).

**Prescrição:** Estruturar e mascarar:
```typescript
logger.info(
  { userId: result.userId, hasCpf: !!result.cpf },
  "user data processed"
);
```

---

### Anti-Pattern 3: Error Message como Stack Trace

```typescript
// ❌ ANTI-PATTERN
catch (e) {
  throw new AppError("ERROR", 500, e.stack); // Stack como mensagem
}
```

**Por quê é ruim:** Stack não é amigável ao usuário; campo "message" fica gigante.

**Prescrição:** Message é pequena, stack va para logger:
```typescript
catch (e) {
  logger.error(
    { stack: e instanceof Error ? e.stack : undefined },
    "operation failed"
  );
  throw new AppError("OPERATION_FAILED", 500, "Unable to complete operation");
}
```

---

### Anti-Pattern 4: Async sem Await

```typescript
// ❌ ANTI-PATTERN
async function handler() {
  logToRemote(message); // Async fire-and-forget (sem await)
  return { status: 200 };
}
// Se logToRemote falhar, handler retorna sucesso
```

**Por quê é ruim:** Race conditions; logs não garantidos.

**Prescrição:** Await ou estruturar como background task:
```typescript
async function handler() {
  await logger.info(...); // Aguarda se crítico
  // OU
  logger.info(...); // Se non-blocking, confiar na library
  return { status: 200 };
}
```

---

### Anti-Pattern 5: Genérico "Error Occurred"

```typescript
// ❌ ANTI-PATTERN
} catch (e) {
  throw new AppError("ERROR", 500, "An error occurred");
}
```

**Por quê é ruim:** Impossível debugar; código é genérico.

**Prescrição:** Message específica ao contexto:
```typescript
} catch (e) {
  const msg = e instanceof Error ? e.message : String(e);
  throw new AppError(
    "SEARCH_FAILED",
    503,
    `Azure AI Search returned: ${msg}`
  );
}
```

---

### Anti-Pattern 6: Missing Structured Data

```typescript
// ❌ ANTI-PATTERN
logger.info("Query executed"); // Sem contexto
```

**Por quê é ruim:** Logs não são machine-readable; Datadog não consegue correlacionar.

**Prescrição:**
```typescript
logger.info(
  { 
    query: q.substring(0, 50), 
    durationMs: elapsed, 
    resultCount: results.length 
  },
  "query executed"
);
```

---

## Validation Checklist

Use ao revisar código gerado por agentes:

- [ ] Nenhum `console.log`, `console.error`, `console.warn`, `console.debug` no código de produção?
- [ ] Toda exceção é capturada e convertida em `AppError` com `code` e `httpStatus`?
- [ ] Handlers deixam exceções subirem (não tratam localmente)?
- [ ] Services/pipeline **podem** tratar AppError interna, mas se não for recuperável, deixam subir?
- [ ] `AppError` contém message específica ao contexto (não "Error occurred")?
- [ ] Logs estruturados: todas as chamadas a `logger.*` têm objeto com dados?
- [ ] Dados sensíveis (email, CPF, senha) **não** são logados?
- [ ] Se stack trace é necessário, vai para logger.error — não para AppError.message?
- [ ] Logger é injetado via construtor ou `createLogger(context)`?
- [ ] Nenhum try/catch silencioso (`.catch(() => {})` sem re-throw)?

---

## Dependencies

### Depende de

- **`typescript-conventions`** (v1.0+) — tipos e Zod para payloads de erro
- **Azure Functions v4** — `InvocationContext` para correlação de logs

### Softwares/Pacotes Usados

- **pino** (^8.0.0) — logger estruturado
- **@azure/functions** (^4.0.0) — contexto de execução
- **zod** (^3.22.0+) — validação (para AppError de validação)

### Referências

- `/src/shared/errors.ts` — Implementação de AppError
- `/src/shared/logger.ts` — Factory de logger
- `/docs/adr/` — Decisões de observabilidade (se houver ADR)

---

## Summary

**error-handling é Foundation porque:**
1. Toda geração de código TypeScript (handler, service, pipeline) passa por erros.
2. Padrão é obrigatório para observabilidade.
3. LLMs naturalmente geram `console.log` e `try/catch` silencioso — precisam ser muito prescritivos.
4. Regras de AppError, pino e não-logging de sensível devem ser aplicadas consistentemente.

**Quando usar:**
- ✅ Revisar qualquer código que trata exceções
- ✅ Gerar novo handler, service, ou pipeline
- ✅ Estruturar logging em qualquer arquivo TypeScript
- ✅ Validar output de agentes IA

**Força desta skill:**
- Prescritividade (DO/DON'T com código real)
- Anti-padrões específicos ao que LLMs geram
- Exemplos que cobrem handlers → services → pipeline (fluxo real do projeto)
