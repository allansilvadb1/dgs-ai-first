# Skills — NovaTech Assistant

> Catálogo de skills reutilizáveis do projeto. A hierarquia segue o modelo **Foundation → Domain → Artifact**: skills de base são pré-requisitos das de domínio, que por sua vez são pré-requisitos das de artefato.

---

## Hierarquia visual

```
skills/
├── foundation/                  ← Regras universais do projeto
│   ├── typescript-conventions   ← Tipagem, Zod, ESM, nomeação
│   ├── error-handling           ← AppError, logger pino, HTTP status
│   └── project-structure        ← Layout de diretórios, onde cada arquivo vive
│
├── domain/                      ← Padrões específicos de cada camada técnica
│   ├── azure-functions-endpoint ← HTTP trigger v4, request/response cycle
│   ├── azure-ai-search-integration ← Retrieval, indexação, scoring
│   ├── react-components         ← Componentes de resultado, feedback e status
│   └── testing-patterns         ← Vitest, fixtures, mocks, cobertura
│
└── artifact/                    ← Receitas completas de artefatos entregáveis
    ├── create-rag-endpoint      ← Endpoint query ponta-a-ponta (Function + Search + LLM)
    ├── create-integration-test  ← Teste de integração de handler HTTP
    └── create-react-card        ← Card de resultado com source_document e feedback
```

**Dependências implícitas:** toda skill de `domain` pressupõe `typescript-conventions` e `error-handling`. Toda skill de `artifact` pressupõe as skills de `domain` correspondentes (ver coluna *Depende de* em cada tabela).

---

## Foundation

Skills que estabelecem a base do projeto. Devem ser lidas antes de qualquer geração de código.

### `typescript-conventions`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `foundation/typescript-conventions.md` |
| **Descrição**    | Convenções de tipagem TypeScript do projeto: uso de Zod para validação de entrada/saída, módulos ESM, nomeação de tipos e interfaces, proibição de `any` implícito, e como estruturar schemas compartilhados em `src/shared/`. |
| **Frase-ativação** | *"crie o schema de validação"*, *"defina o tipo de resposta"*, *"qual a interface correta para X"*, *"adicione tipagem forte"*, *"valide o payload com Zod"* |
| **Quem cria**    | Tech Lead |
| **Quem consome** | Devs (Backend e Frontend) · Agentes de geração de código (Copilot, Claude Code) |
| **Frequência**   | **Alta** — toda geração de código TypeScript no projeto |
| **Depende de**   | — |

---

### `error-handling`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `foundation/error-handling.md` |
| **Descrição**    | Padrão de erros do projeto: classe `AppError` com `code` e `httpStatus`, logger estruturado via `pino` (sem `console.log`), mapeamento de erros para respostas HTTP bem formadas, e como propagar erros entre camadas (handler → service → pipeline). |
| **Frase-ativação** | *"como tratar erros neste projeto"*, *"adicione tratamento de exceção"*, *"o endpoint deve retornar 400 quando"*, *"log de erro estruturado"*, *"erro não tratado no handler"* |
| **Quem cria**    | Tech Lead |
| **Quem consome** | Devs (Backend e Frontend) · QA · Agentes de geração de código |
| **Frequência**   | **Alta** — todo handler, service e pipeline usa este padrão |
| **Depende de**   | `typescript-conventions` |

---

### `project-structure`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `foundation/project-structure.md` |
| **Descrição**    | Mapa do repositório: onde vive cada tipo de arquivo (`src/functions/`, `src/pipeline/`, `src/web/`, `src/shared/`, `tests/unit/`, `tests/integration/`, `specs/`, `skills/`, `docs/`), convenção de nomes de arquivos, e regras de co-localização (spec ao lado do código, fixture em `tests/fixtures/`). |
| **Frase-ativação** | *"onde devo criar este arquivo"*, *"qual diretório correto para"*, *"mova este módulo para o lugar certo"*, *"estrutura do projeto"*, *"organize as pastas"* |
| **Quem cria**    | Tech Lead |
| **Quem consome** | Devs · QA · Delivery Manager · Agentes de geração e navegação de código |
| **Frequência**   | **Alta** — toda criação de arquivo novo |
| **Depende de**   | — |

---

## Domain

Skills específicas de cada camada técnica. Descrevem padrões de implementação dentro de um contexto tecnológico.

### `azure-functions-endpoint`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `domain/azure-functions-endpoint.md` |
| **Descrição**    | Como criar um HTTP trigger com Azure Functions v4 em TypeScript: registro da função, ciclo `HttpRequest → validate → execute → HttpResponse`, uso do `InvocationContext` para logging, separação entre `handler.ts` / `validator.ts` / `response-builder.ts`, e contrato de resposta padrão do projeto. |
| **Frase-ativação** | *"crie um novo endpoint HTTP"*, *"implemente o handler da Function"*, *"adicione uma rota no backend"*, *"como registrar uma Azure Function"*, *"endpoint de feedback/health/query"* |
| **Quem cria**    | Tech Lead · Dev Backend |
| **Quem consome** | Dev Backend · QA · Agentes de geração de código (especialmente ao gerar `handler.ts`) |
| **Frequência**   | **Alta** — cada novo endpoint (query, feedback, health) segue este padrão |
| **Depende de**   | `typescript-conventions`, `error-handling` |

---

### `azure-ai-search-integration`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `domain/azure-ai-search-integration.md` |
| **Descrição**    | Como integrar com Azure AI Search no pipeline RAG: configuração do `SearchClient`, construção de queries híbridas (keyword + vector), extração de `source_document` dos resultados, score mínimo de relevância, e como expor os chunks para o prompt do modelo de linguagem. |
| **Frase-ativação** | *"busque no índice de documentos"*, *"faça o retrieval dos chunks"*, *"integre com Azure AI Search"*, *"query híbrida semântica"*, *"indexe este documento no corpus"* |
| **Quem cria**    | Tech Lead · Dev Backend |
| **Quem consome** | Dev Backend · Agentes de geração do pipeline RAG |
| **Frequência**   | **Média** — restrita ao pipeline de retrieval (`src/pipeline/`, `src/services/`) |
| **Depende de**   | `typescript-conventions`, `error-handling`, `azure-functions-endpoint` |

---

### `react-components`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `domain/react-components.md` |
| **Descrição**    | Padrões de componentes React do painel web NovaTech: estrutura de `props` tipadas com TypeScript, uso de hooks (`useState`, `useEffect`) para estado de loading/erro, convenção de nomes de arquivos (`.tsx`), e como compor componentes de resultado, feedback e status no layout de `src/web/src/`. |
| **Frase-ativação** | *"crie um componente React"*, *"implemente a interface do painel"*, *"adicione estado de carregamento"*, *"componente de exibição de resultado"*, *"hook para chamar o endpoint"* |
| **Quem cria**    | Tech Lead · Dev Frontend |
| **Quem consome** | Dev Frontend · Agentes de geração de UI |
| **Frequência**   | **Média** — restrita à camada `src/web/` |
| **Depende de**   | `typescript-conventions`, `error-handling` |

---

### `testing-patterns`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `domain/testing-patterns.md` |
| **Descrição**    | Padrões de testes com Vitest: pirâmide de testes do projeto (unit / integration / e2e), uso de fixtures em `tests/fixtures/`, como mockar serviços externos (Azure AI Search, modelo LLM) em testes unitários, e quando escrever testes de integração reais contra stubs locais. |
| **Frase-ativação** | *"escreva um teste para"*, *"adicione cobertura de testes"*, *"como mockar o SearchClient"*, *"teste unitário do handler"*, *"fixture de chunk para o teste"* |
| **Quem cria**    | QA · Tech Lead |
| **Quem consome** | Devs · QA · Agentes de geração de testes |
| **Frequência**   | **Alta** — todo artefato de código novo deve ter teste associado |
| **Depende de**   | `typescript-conventions`, `error-handling`, `project-structure` |

---

## Artifact

Receitas completas de artefatos entregáveis. Cada skill de artefato combina skills de domínio para guiar a criação de um entregável concreto, do início ao fim.

### `create-rag-endpoint`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `artifact/create-rag-endpoint.md` |
| **Descrição**    | Passo a passo para criar um endpoint RAG ponta-a-ponta: (1) validar `QueryInput` com Zod, (2) recuperar chunks via Azure AI Search, (3) montar o prompt com contexto e `source_document`, (4) chamar o modelo de linguagem, (5) construir `QueryResponse` com referências, (6) registrar handler na Function v4. Inclui checklist de erros esperados e contratos de I/O. |
| **Frase-ativação** | *"implemente o endpoint de consulta completo"*, *"crie o query endpoint RAG"*, *"endpoint que busca documentos e responde com o modelo"*, *"fluxo completo de pergunta e resposta"* |
| **Quem cria**    | Tech Lead · Dev Backend (par ou individual) |
| **Quem consome** | Dev Backend · Agentes de geração de código — é o artefato central do projeto |
| **Frequência**   | **Baixa** — artefato de alta complexidade; criado uma vez por funcionalidade de consulta |
| **Depende de**   | `azure-functions-endpoint`, `azure-ai-search-integration`, `typescript-conventions`, `error-handling` |

---

### `create-integration-test`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `artifact/create-integration-test.md` |
| **Descrição**    | Como escrever um teste de integração para um handler HTTP da Azure Function: montar o `HttpRequest` de stub, invocar o handler diretamente (sem rede), verificar o `HttpResponse` com status e body esperados, e usar fixtures de chunks em `tests/fixtures/` para simular o retorno do Search. |
| **Frase-ativação** | *"crie um teste de integração para o handler"*, *"teste que valida o endpoint sem subir a Function"*, *"integration test do query endpoint"*, *"teste com fixture de chunk real"* |
| **Quem cria**    | QA · Dev Backend |
| **Quem consome** | QA · Dev Backend · Agentes de geração de testes |
| **Frequência**   | **Média** — um por endpoint ou fluxo crítico novo |
| **Depende de**   | `testing-patterns`, `azure-functions-endpoint`, `typescript-conventions` |

---

### `create-react-card`

| Campo            | Detalhe |
|------------------|---------|
| **Arquivo**      | `artifact/create-react-card.md` |
| **Descrição**    | Como criar um card de resultado React para o painel NovaTech: props `answer`, `sourceDocument`, `confidence`; exibição condicional de loading/erro; botão de feedback integrado ao endpoint `/feedback`; e estilização consistente com o Design System do projeto. |
| **Frase-ativação** | *"crie o card de resultado da busca"*, *"componente que exibe resposta e fonte"*, *"card com botão de feedback"*, *"mostre o source_document no painel"* |
| **Quem cria**    | Dev Frontend |
| **Quem consome** | Dev Frontend · Agentes de geração de UI |
| **Frequência**   | **Baixa** — artefato de UI específico; criado uma vez por tipo de resultado exibido |
| **Depende de**   | `react-components`, `typescript-conventions` |

---

## Resumo de frequência e cobertura

| Skill                          | Camada     | Frequência | Cria               | Consome                            |
|-------------------------------|------------|------------|--------------------|------------------------------------|
| `typescript-conventions`       | Foundation | Alta       | Tech Lead          | Devs, Agentes                      |
| `error-handling`               | Foundation | Alta       | Tech Lead          | Devs, QA, Agentes                  |
| `project-structure`            | Foundation | Alta       | Tech Lead          | Devs, QA, DM, Agentes             |
| `azure-functions-endpoint`     | Domain     | Alta       | Tech Lead, Dev BE  | Dev BE, QA, Agentes                |
| `testing-patterns`             | Domain     | Alta       | QA, Tech Lead      | Devs, QA, Agentes                  |
| `azure-ai-search-integration`  | Domain     | Média      | Tech Lead, Dev BE  | Dev BE, Agentes do pipeline        |
| `react-components`             | Domain     | Média      | Tech Lead, Dev FE  | Dev FE, Agentes de UI              |
| `create-integration-test`      | Artifact   | Média      | QA, Dev BE         | QA, Dev BE, Agentes                |
| `create-rag-endpoint`          | Artifact   | Baixa      | Tech Lead, Dev BE  | Dev BE, Agentes (artefato central) |
| `create-react-card`            | Artifact   | Baixa      | Dev FE             | Dev FE, Agentes de UI              |

---

## Como os agentes devem usar este catálogo

1. **Leitura obrigatória antes de gerar código:** sempre carregar a skill `project-structure` e `typescript-conventions`.
2. **Detecção de contexto:** identificar a frase-ativação no prompt do usuário e carregar a skill correspondente.
3. **Encadeamento:** ao usar uma skill de `artifact`, carregar também as skills de `domain` listadas em *Depende de*.
4. **Atualização:** quando um padrão mudar no projeto, atualizar o arquivo `.md` da skill antes de gerar novo código.
