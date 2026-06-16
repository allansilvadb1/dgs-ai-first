# Tasks — Query Endpoint

> Derivado de `plan.md`. Estimativas: **P** (< 4h) · **M** (4–16h) · **G** (> 16h)

---

## T-01 — Scaffold do projeto Azure Functions v4 (TypeScript)

**Descrição:** Inicializar a estrutura de pacote para a Azure Function HTTP trigger, incluindo `package.json`, `tsconfig.json`, `host.json` e a definição da função em TypeScript com Azure Functions v4 programming model.

**Critérios de aceite:**
- [ ] `func start` sobe localmente sem erros de compilação
- [ ] `GET /api/query` retorna 405 Method Not Allowed (rota existe mas ainda não aceita GET)
- [ ] `POST /api/query` retorna 200 com body `{"status":"ok"}` (stub)
- [ ] `tsc --noEmit` passa sem erros

**Dependências:** nenhuma

**Estimativa:** P

---

## T-02 — Schema de validação de input/output com Zod

**Descrição:** Definir e exportar os schemas Zod para o body do request (`{ question: string }`) e para o response (`{ answer: string, source_documents: string[] }`), com mensagens de erro descritivas.

**Critérios de aceite:**
- [ ] `RequestSchema.parse({ question: "" })` lança erro com mensagem clara (string vazia inválida)
- [ ] `RequestSchema.parse({ question: "texto" })` retorna objeto tipado sem erro
- [ ] `ResponseSchema.parse({})` lança erro listando campos faltantes
- [ ] Tipos TypeScript inferidos por `z.infer<>` são usados no handler sem castings manuais
- [ ] Testes unitários cobrem casos válido, campo ausente e tipo errado

**Dependências:** T-01

**Estimativa:** P

---

## T-03 — Integração com Azure OpenAI para geração de embedding

**Descrição:** Implementar função `getEmbedding(question: string): Promise<number[]>` que chama o deployment de embeddings no Azure OpenAI e retorna o vetor resultante.

**Critérios de aceite:**
- [ ] Função retorna array de números com dimensão correta (ex.: 1536 para `text-embedding-ada-002`)
- [ ] Variáveis de ambiente necessárias (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`) são documentadas em `.env.example`
- [ ] Chamada com `question` vazia lança erro antes de chamar a API
- [ ] Teste de integração (requer credenciais reais ou mock) valida o contrato do retorno

**Dependências:** T-01

**Estimativa:** P

---

## T-04 — Integração com Azure AI Search para busca dos top-5 chunks

**Descrição:** Implementar função `searchChunks(embedding: number[]): Promise<Chunk[]>` que executa busca vetorial no índice do Azure AI Search e retorna os 5 chunks mais relevantes com campos `content` e `source_document`.

**Critérios de aceite:**
- [ ] Retorna exatamente até 5 resultados (configurável via constante `TOP_K = 5`)
- [ ] Cada item do retorno contém `content: string` e `source_document: string`
- [ ] Variáveis de ambiente (`AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX_NAME`) documentadas em `.env.example`
- [ ] Se o índice não contiver resultados, retorna array vazio sem lançar exceção
- [ ] Teste com mock do cliente valida a estrutura do payload enviado ao Search

**Dependências:** T-01

**Estimativa:** P

---

## T-05 — Montagem do prompt respeitando o context budget

**Descrição:** Implementar função `buildPrompt(systemPrompt: string, chunks: Chunk[], question: string): string` que compõe o prompt final garantindo o budget de ~4 K tokens para system prompt e ~8 K tokens para chunks, truncando chunks excedentes se necessário.

**Critérios de aceite:**
- [ ] Com 5 chunks dentro do budget, todos são incluídos no prompt
- [ ] Com chunks que excedem 8 K tokens, os de menor score são descartados e um aviso é logado
- [ ] O system prompt é lido de `/prompts/system-prompt.md` (caminho configurável)
- [ ] Função é pura (sem side effects) e testável unitariamente
- [ ] Testes unitários cobrem: abaixo do limite, exatamente no limite e acima do limite

**Dependências:** T-02, T-04

**Estimativa:** M

---

## T-06 — Chamada ao GPT-4o para geração da resposta

**Descrição:** Implementar função `generateAnswer(prompt: string): Promise<string>` que envia o prompt ao deployment GPT-4o no Azure OpenAI e retorna o texto da resposta.

**Critérios de aceite:**
- [ ] Retorna string não-vazia para prompt válido
- [ ] Variável `AZURE_OPENAI_CHAT_DEPLOYMENT` documentada em `.env.example`
- [ ] Erros da API (4xx/5xx) são relançados como erros tipados (não strings genéricas)
- [ ] Teste com mock valida que o payload enviado contém `messages` no formato correto

**Dependências:** T-01

**Estimativa:** P

---

## T-07 — Wiring do handler HTTP completo (pipeline end-to-end)

**Descrição:** Conectar T-02 → T-03 → T-04 → T-05 → T-06 no handler `POST /api/query`, validar input com Zod, retornar `{ answer, source_documents }` serializado como JSON com status 200, e tratar erros de validação com status 400.

**Critérios de aceite:**
- [ ] `POST /api/query` com `{ "question": "Qual a política de férias?" }` retorna 200 com `answer` e `source_documents`
- [ ] `POST /api/query` com body inválido retorna 400 com mensagem de erro descritiva
- [ ] `POST /api/query` com erro de upstream retorna 502 (não vaza stack trace)
- [ ] Content-Type da resposta é `application/json`
- [ ] Teste de integração local (com variáveis reais ou mocks) cobre os três cenários acima

**Dependências:** T-02, T-03, T-04, T-05, T-06, T-08, T-09

**Estimativa:** M

---

## T-08 — Retry com exponential backoff para chamadas Azure

**Descrição:** Implementar utilitário `withRetry<T>(fn: () => Promise<T>, opts): Promise<T>` com exponential backoff (base 500ms, máx 3 tentativas) e aplicá-lo nas chamadas de T-03, T-04 e T-06.

**Critérios de aceite:**
- [ ] Em caso de erro 429 ou 503, a função retenta até 3 vezes antes de lançar
- [ ] Intervalo entre tentativas segue backoff exponencial (500ms, 1000ms, 2000ms ± jitter)
- [ ] Erros 400 (cliente) não são retentados
- [ ] Testes unitários verificam número de chamadas e intervalos usando fake timers

**Dependências:** T-01

**Estimativa:** P

---

## T-09 — Structured logging com pino

**Descrição:** Configurar instância global do `pino` com nível de log controlado por variável de ambiente `LOG_LEVEL` e adicionar logs estruturados nos pontos-chave do pipeline: recebimento do request, tempo de cada chamada externa e erros.

**Critérios de aceite:**
- [ ] Logs emitidos em formato JSON (não texto livre) quando `NODE_ENV=production`
- [ ] Cada log de chamada externa inclui campos `durationMs` e `service`
- [ ] Logs de erro incluem `err.message` e `err.stack`
- [ ] `LOG_LEVEL` documentado em `.env.example`; padrão `info`
- [ ] Nenhum `console.log` no código de produção

**Dependências:** T-01

**Estimativa:** P

---

## T-10 — Teste de integração end-to-end

**Descrição:** Escrever suite de testes de integração que sobem a função localmente (ou via emulador) e exercitam o fluxo completo com dados reais do índice de test (populado pelo pipeline de ingestão), validando a resposta e os metadados de source_document.

**Critérios de aceite:**
- [ ] Pergunta sobre um documento presente no índice retorna `source_documents` contendo o nome esperado
- [ ] Pergunta fora do domínio retorna resposta sem alucinação (source_documents vazio ou com aviso)
- [ ] Suite executa em CI sem intervenção manual (credenciais via secrets)
- [ ] Tempo total de execução da suite < 60 segundos

**Dependências:** T-07, índice de test populado (pipeline de ingestão)

**Estimativa:** G
