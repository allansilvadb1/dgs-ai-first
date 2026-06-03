# Análise Técnica Final — Assistente de IA NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Cliente:** NovaTech Logística  
**Contratante:** DB1 Group  
**Data da análise:** 2026-06-03  
**Responsável:** Allan Silva  
**Stack-alvo:** Microsoft 365 E3 + Azure AI Services  

---

## Sumário Executivo

A NovaTech possui uma base documental de aproximadamente **4,1 milhões de tokens** distribuída em 800 PDFs, 400 páginas de wiki e 50 planilhas, com atualização mensal descentralizada em três áreas. O objetivo é reduzir o tempo médio de busca por informação de **12 minutos para menos de 2 minutos** por chamado, num volume de aproximadamente 192 consultas documentais por dia.

A análise técnica conduzida nesta sessão identificou que a viabilidade do assistente é alta, mas condicionada à resolução de cinco problemas estruturais: heterogeneidade das fontes, coexistência de versões conflitantes de documentos, mistura de fontes com diferentes níveis de confiabilidade, degradação silenciosa por reindexação tardia, e risco de o LLM realizar cálculos aritméticos de forma autônoma. Cada um desses problemas tem estratégia de mitigação concreta mapeada abaixo.

---

## Histórico de Iteração da Análise

### Iteração 1 — Viabilidade Técnica e Desafios do Pipeline RAG

**Problema levantado pelo Tech Lead:**
Avaliar a viabilidade técnica considerando as características da documentação (tabelas com 15+ colunas, fluxogramas como imagens, OCR necessário, macros do Confluence, fórmulas interdependentes) e o impacto do gerenciamento de contexto.

**Análise:**

A viabilidade é confirmada, mas o pipeline de RAG enfrenta desafios em quatro frentes:

**Ingestão heterogênea**

| Fonte | Problema | Estratégia |
|---|---|---|
| PDFs com tabelas de 15+ colunas | Chunking por token quebra tabelas no meio de linhas | Azure Document Intelligence para extração estruturada; chunks de tabela inteira com cabeçalho replicado |
| PDFs escaneados | OCR de qualidade variável gera ruído indexado | Azure Document Intelligence com pipeline de OCR; flag de confiança por chunk |
| Fluxogramas embutidos como imagem | Ignorados pelo pipeline de texto | Conversão manual para texto estruturado (PlantUML, Mermaid, ou descrição de passos) |
| Confluence com macros customizadas | Exportação texto plano não renderiza macros | Exportação via API do Confluence (HTML renderizado) |
| Planilhas com fórmulas interdependentes | Fórmulas não avaliam durante ingestão | Pré-computação de valores em documento derivado |

**Documentos conflitantes no mesmo índice**

PROC-042 v1 e v2 coexistem sem hierarquia clara. O retrieval retorna chunks de ambas para a mesma query. O LLM recebe dois conjuntos de multiplicadores contraditórios sem saber qual é o vigente.

Contradições documentadas:

| Parâmetro | PROC-042 v1 | PROC-042 v2 |
|---|---|---|
| Multiplicador Sul | 1.2 | 1.3 |
| Multiplicador Sudeste | 1.0 | 1.1 |
| Multiplicador Nordeste | 1.4 | 1.5 |
| Multiplicador Norte | 1.6 | 1.8 |
| Fator de peso (1.001–3.000kg) | 1.2 | 1.15 |
| Fator de peso (> 3.000kg) | 1.5 | 1.4 |
| Prazo adicional | +2 dias úteis | +3 dias úteis |

Mitigação: metadados de versão e data em cada chunk; filtro de preferência por data mais recente no retrieval; system prompt instruindo sinalização explícita de contradição; processo de deprecação formal a estabelecer com a NovaTech.

**FAQ informal misturado com documentos normativos**

O `FAQ-Atendimento` não possui dono formal, não passa por Compliance e pode estar desatualizado. Indexado no mesmo espaço vetorial que POL-001 e SLA-2024, o assistente pode responder perguntas críticas citando o FAQ com a mesma confiança da política oficial.

Mitigação: índices separados por tier de confiança (`formal`: POL, PROC, SLA / `informal`: FAQ); pipeline de recuperação prioriza o índice formal; source attribution explícita na resposta.

**Context Engineering e Lost in the Middle**

Com múltiplos chunks no contexto, informação relevante posicionada no meio da janela é subponderada pelo modelo (Liu et al., 2023). Estratégia: reranking para selecionar top 3–4 chunks; posicionamento do chunk mais relevante no início do contexto.

**Arquitetura resultante:**

```
Ingestão
  └─ Azure Document Intelligence (OCR + tabelas estruturadas)
  └─ Chunking semântico com metadados (doc_id, version, date, tier)
  └─ Índices separados: formal / informal

Retrieval
  └─ Query decomposition para perguntas multi-domínio
  └─ Busca prioritária no índice formal
  └─ Reranking top-15 → top-6 com score mínimo de corte
  └─ Filtro de preferência por versão mais recente

Context Assembly
  └─ Orçamento por componente (system prompt / histórico / chunks)
  └─ Chunk mais relevante posicionado no início
  └─ Cabeçalho de fonte embutido em cada chunk

LLM
  └─ Instrução de citação de fonte obrigatória
  └─ Instrução de sinalização de contradição
  └─ Proibição de extrapolação para perguntas sem cobertura
```

---

### Iteração 2 — Estratégias de Ingestão que Requerem Intervenção Manual

**Problema levantado:**
Das estratégias de ingestão, identificar aquelas que não podem ser automatizadas e exigem ação humana — diferenciando responsabilidade entre desenvolvedor e cliente.

**Análise:**

**Intervenção do desenvolvedor (recorrente)**

*Fluxogramas embutidos como imagem*

O pipeline de texto ignora imagens. Para cada documento com fluxograma, o desenvolvedor produz um equivalente textual descrevendo o procedimento (PlantUML, Mermaid, ou lista de passos). Esse trabalho é **refeito a cada atualização do fluxograma original** — o que, dado o ciclo mensal da NovaTech, representa esforço operacional contínuo se não for mapeado no escopo do projeto.

*Planilhas com fórmulas interdependentes*

As fórmulas não avaliam durante a ingestão. O desenvolvedor abre cada planilha, identifica os valores calculados relevantes para o atendimento, e produz um documento derivado com os resultados computados — não as fórmulas. Exemplo: em vez de `=B3*C3*fator_regional`, o documento indexado contém `"Frete para 600kg no Nordeste: fator total 1.50 sobre a tarifa base"`. Reprocessamento necessário a cada ciclo mensal de atualização das planilhas.

**Intervenção do cliente / NovaTech (processo a estabelecer)**

*Macros customizadas do Confluence*

A exportação do Confluence em texto plano não renderiza macros — o conteúdo aparece como código de macro no índice. Duas saídas: (a) NovaTech converte o conteúdo das macros para texto estático nas páginas afetadas; ou (b) desenvolvedor usa a API do Confluence para exportar HTML renderizado, com validação do cliente para confirmar que o conteúdo renderizado está correto.

*Governança de versões — deprecação de documentos*

A estratégia técnica de filtrar chunks por data mais recente resolve o sintoma mas não o problema de raiz: cada ciclo de atualização pode gerar novos pares conflitantes. A NovaTech precisa estabelecer processo formal de deprecação — quem publica uma nova versão de um PROC também marca a versão anterior como obsoleta no SharePoint. Sem esse processo, o esforço de identificação e tratamento de conflitos recai sobre o desenvolvedor a cada ciclo de reindexação.

**Implicação para o escopo do projeto**

Fluxogramas e planilhas representam esforço recorrente mensal. Se não forem mapeados explicitamente nos 3 meses de escopo (discovery + desenvolvimento + go-live), o custo de manutenção emerge como surpresa após o go-live, comprometendo a sustentabilidade do sistema.

---

### Iteração 3 — Estimativa do Tamanho da Base de Tokens

**Problema levantado:**
Estimar a base total de tokens para os 800 PDFs (10 páginas em média), 400 páginas wiki (1.500 palavras em média) e 50 planilhas, usando ~0,75 palavras por token.

**Análise:**

| Fonte | Cálculo | Tokens |
|---|---|---|
| PDFs | 800 × 10 pág × 300 palavras ÷ 0,75 | **3.200.000** |
| Wiki Confluence | 400 × 1.500 palavras ÷ 0,75 | **800.000** |
| Planilhas | 50 × 2.000 palavras (serializado) ÷ 0,75 | **133.000** |
| **Total** | | **~4.133.000** |

**Estimativa ajustada pós-pré-processamento** (fluxogramas convertidos + macros resolvidas + planilhas derivadas): **~4,5M–4,8M tokens**.

**Comparação com janelas de contexto disponíveis:**

| Modelo | Janela máxima | % da base que cabe |
|---|---|---|
| Claude Sonnet / GPT-4o | 128K–200K tokens | ~4,8% |
| Gemini 1.5 Pro | 1M tokens | ~24% |
| Base NovaTech | 4,1M tokens | — |

**Conclusão:** RAG não é uma escolha arquitetural — é um requisito estrutural. Nenhum modelo atual comporta a base inteira em contexto.

---

### Iteração 4 — Orçamento de Contexto e o Problema dos 252 Chunks

**Problema levantado:**
Com GPT-4o (128K tokens) e system prompt de ~2K tokens, teríamos matematicamente 252 chunks de 500 tokens disponíveis por query. Como avaliar essa situação?

**Análise:**

252 chunks por query é um cenário de degradação severa, não de capacidade.

**Decomposição do orçamento real:**

```
128.000 tokens (janela total)
─────────────────────────────────────
  - 2.000  system prompt + instruções
  - 1.500  histórico de conversa (últimas 3–5 trocas)
  -   300  pergunta + metadados
─────────────────────────────────────
≈ 124.200 tokens "disponíveis" → 248 chunks teóricos
```

**Por que 252 chunks destrói a qualidade:**

*Lost in the Middle em escala:*
```
Chunk 1–5      → modelo presta atenção ✓
Chunk 6–246    → zona de degradação severa ✗
Chunk 247–252  → modelo presta atenção ✓
```

*Contradições insolúveis:* com 252 chunks, PROC-042-v1 e v2 certamente coexistem no contexto. O modelo tem 252 fragmentos para reconciliar — probabilidade alta de escolher a versão errada sem sinalizar.

*Custo operacional:* processar 126K tokens de contexto por query a ~192 queries/dia multiplica o custo por query em relação ao contexto otimizado.

**Orçamento prático recomendado:**

| Componente | Tokens | Chunks |
|---|---|---|
| System prompt + instruções | 2.000 | — |
| Histórico de conversa | 1.500 | — |
| Pergunta + metadados | 300 | — |
| **Chunks recuperados** | **3.000–5.000** | **6–10** |
| Buffer de segurança | 500 | — |
| **Total usado** | **~7.300–9.300** | — |

**Escala do problema de retrieval:**
```
4.100.000 ÷ 500 = ~8.200 chunks no índice
6–10 chunks por query = 0,07%–0,12% da base por pergunta
```

A janela de 128K não é solução — é margem de segurança. O trabalho real está no reranking e na precisão do retrieval.

---

### Iteração 5 — Estratégia de Chunking

**Problema levantado:**
Recomendar uma estratégia de chunking justificada pelo tipo de pergunta que o usuário fará e pelo conceito de *lost in the middle*.

**Análise:**

**Premissa:** o tamanho do chunk deve ser determinado pelo tipo de resposta que a pergunta exige, não por um valor fixo de tokens.

**Tipos de pergunta e necessidade de chunk:**

*Lookup pontual* — "Qual o prazo de devolução?" / "Qual o SLA do Gold para incidente crítico?"
Precisam de um fato específico isolado. Chunk grande entrega a resposta enterrada em ruído.

*Procedural* — "Como abro um chamado de devolução?" / "Quais documentos preciso para frete especial?"
Precisam de sequência completa de passos. Fragmentar o procedimento em dois chunks garante que o retrieval traga apenas metade do processo.

*Cálculo com tabela* — "Qual o frete para 600kg para Manaus?"
Precisam da fórmula e dos valores da tabela juntos. Chunks separados para fórmula e multiplicadores garantem que o LLM receba apenas metade da informação.

**Chunking diferenciado por tipo de conteúdo:**

| Tipo de conteúdo | Tamanho | Overlap | Lógica de corte |
|---|---|---|---|
| Valores tabelados (SLA, multiplicadores) | 150–250 tokens | 0 | Uma seção lógica com cabeçalho replicado |
| Passos procedurais (listas numeradas) | 300–500 tokens | 50 tokens | Limite de etapa — nunca no meio de um passo |
| Regras + exceções (POL-001) | 250–400 tokens | 75 tokens | Regra e suas exceções no mesmo chunk |
| Itens de FAQ | 100–200 tokens | 0 | Um par pergunta/resposta por chunk |
| Texto narrativo (contexto, definições) | 300–400 tokens | 75 tokens | Limite de parágrafo |

**Cabeçalho de contexto — mitigação do lost in the middle:**

Todo chunk abre com uma linha de fonte embutida no texto:

```
[POL-001 v3.1 | Seção 3.1 | Prazo de devolução]
O cliente pode solicitar devolução em até 7 dias úteis após
a data de recebimento confirmada no sistema de tracking...
```

Quando o chunk está na posição 5 de 8 no contexto, o modelo lê o cabeçalho e ancora a informação numa fonte identificada. Sem o cabeçalho, chunks em posição central são texto anônimo subponderado.

**Aplicação aos documentos da NovaTech:**

*SLA-2024:* cinco chunks separados (tiers, SLA geral, SLA crítico, definição de crítico, penalidades). Pergunta "qual o SLA do Gold para incidente crítico?" recupera apenas o Chunk C — 150 tokens com a resposta exata.

*PROC-042-v2:* fórmula e multiplicadores no mesmo chunk — uma unidade de cálculo completa, não dividida.

```
[PROC-042 v2.0 | Seção 2 | Fórmula e multiplicadores regionais]
Frete = Valor base × Multiplicador regional × Fator de peso
Fatores: 1.0 (500–1.000kg) | 1.15 (1.001–3.000kg) | 1.4 (>3.000kg)
Multiplicadores: Sul 1.3 | Sudeste 1.1 | Centro-Oeste 1.4 | Nordeste 1.5 | Norte 1.8
```

*POL-001:* regra geral e exceções no mesmo chunk. Pergunta "carga perigosa pode ser devolvida?" exige as duas — sem isso, o modelo pode responder afirmativamente com base na regra geral sem ver a exceção imediatamente abaixo.

**Efeito no orçamento de contexto:**

```
10 chunks × 500 tokens = 5.000 tokens → 1 domínio coberto
10 chunks × 250 tokens = 2.500 tokens → 2–3 domínios cobertos
```

Para perguntas multi-domínio (devolução + frete especial + carga perigosa), isso é a diferença entre resposta completa e resposta parcial.

---

### Iteração 6 — Cálculos Aritméticos: Impedir que o LLM Calcule

**Problema levantado:**
O modelo pode receber a fórmula do PROC-042 via chunk e tentar calcular autonomamente. Como garantir que o LLM não seja responsável pelos cálculos?

**Análise:**

Três abordagens complementares, não discutidas anteriormente:

**Tool Calling (Function Calling) — abordagem primária**

O LLM identifica os parâmetros necessários e delega o cálculo a uma função registrada. A aritmética acontece em código determinístico — o LLM nunca toca nos números.

```
Usuário: "Qual o frete para 600kg para Manaus?"
  │
  ├─ LLM extrai: { peso: 600, regiao: "Norte" }
  ├─ LLM chama: calcular_frete(peso=600, regiao="Norte")
  ├─ Função executa: base × 1.8 × 1.0
  └─ LLM apresenta: "O frete é R$ X, conforme PROC-042 v2"
```

Tools candidatas para a NovaTech:
- `calcular_frete(peso, regiao)` — aplica PROC-042-v2 com tarifa vigente
- `verificar_sla(tier_cliente, tipo_chamado)` — retorna prazos sem consultar tabela
- `calcular_prazo_entrega(rota, peso)` — prazo padrão + dias adicionais

**Pré-computação da grade de resultados**

Para espaços de entrada finitos (3 faixas de peso × 5 regiões = 15 combinações), pré-computar todos os fatores e indexar como fatos:

```
[PROC-042 v2 | Fatores combinados | Nordeste]
500–1.000kg → Nordeste: fator total = 1.5 × 1.0 = 1.50
1.001–3.000kg → Nordeste: fator total = 1.5 × 1.15 = 1.725
> 3.000kg → Nordeste: fator total = 1.5 × 1.4 = 2.10
```

O LLM não vê a fórmula — recupera o resultado. Limitação: o documento derivado precisa ser regerado a cada atualização mensal da planilha de tarifa base.

**Semantic Router com Intent Classification**

Uma camada de roteamento antes do RAG classifica a intenção da query. Queries do tipo `calculation` nunca chegam ao pipeline RAG com a fórmula — são redirecionadas direto ao serviço de cálculo, que retorna o valor para o LLM apenas formatar.

```
Query → Classifier → intent: calculation → Serviço de cálculo → Resultado → LLM (formata)
                   → intent: lookup      → Pipeline RAG → LLM (responde)
```

Benefício adicional: queries de cálculo não arriscam trazer chunks da PROC-042-v1, porque o serviço está parametrizado com a versão correta e independe do retrieval.

**Comparação das abordagens:**

| Abordagem | Elimina aritmética do LLM | Atualização de tabela | Complexidade |
|---|---|---|---|
| Tool Calling | Total | Automática (busca tarifa live) | Média |
| Pré-computação da grade | Total | Manual/script mensal | Baixa |
| Semantic Router | Total | Centralizada no serviço | Alta |

**Recomendação:** Tool Calling como mecanismo principal + Pré-computação como fallback para integração offline (ex: Teams sem conectividade com o serviço de cálculo).

---

### Iteração 7 — Degradação Silenciosa e Staleness do Índice

**Problema levantado:**
Os documentos são atualizados mensalmente. Durante a janela entre a atualização e a reindexação, o assistente responde com a versão antiga — e ninguém percebe porque a resposta ainda parece coerente. Nenhum mecanismo de alerta ou monitoramento havia sido discutido.

**Análise:**

Três camadas complementares de proteção:

**Camada 1 — Prevenção: Reindexação Orientada a Eventos**

A Microsoft Graph API expõe webhooks de change notification para o SharePoint. Quando um documento é modificado, o SharePoint notifica um endpoint externo em segundos.

```
SharePoint (doc atualizado)
  └─ Webhook → Azure Function
      ├─ Remove chunks antigos do índice (por doc_id)
      ├─ Processa novo documento (OCR, chunking, embedding)
      └─ Insere novos chunks com updated_at atualizado
```

O Confluence tem API REST com eventos de modificação de página — mesmo padrão. Planilhas no OneDrive também são cobertas pelo webhook do SharePoint.

**O que o webhook não cobre:** documentos editados fora do SharePoint antes do upload, e a janela entre o upload e o processamento completo (minutos para documentos com OCR).

**Camada 2 — Detecção: Metadado de Frescor e Auditoria de Hash**

*Metadado de frescor por chunk:*
```
source_modified_at: 2024-11-10T14:32:00Z
indexed_at:         2024-11-10T14:45:00Z
```

Job diário: percorre o índice, consulta a API do SharePoint pela data de modificação atual de cada documento, compara com `indexed_at`. Qualquer chunk com `source_modified_at > indexed_at` entra na fila de reprocessamento — capturando o que o webhook perdeu.

*Auditoria por hash de conteúdo:*
Na ingestão, armazena-se o hash SHA-256 do documento. O job diário recalcula o hash na fonte e compara. Se diferente → mudança detectada → reindexação disparada. Captura mudanças que preservam o `modified_at` (substituição de arquivo com timestamp mantido).

**Camada 3 — Mitigação: Tornar o Staleness Visível**

*Aviso de frescor inline na resposta:*
Se um chunk utilizado tem `indexed_at` sem confirmação de atualidade há mais de N dias (threshold recomendado: 35 dias para o ciclo mensal da NovaTech), o sistema injeta aviso automático:

```
"[⚠️ Documento indexado em 10/11/2023 — confirme no SharePoint
  se há versão mais recente antes de usar esta informação.]"
```

*Penalidade de frescor no reranking:*
Chunks com staleness suspeito recebem penalidade no score. O sistema prefere chunks recentes quando há alternativas — sem bloquear completamente, mas priorizando confiabilidade.

*Dashboard de divergência para operações:*
Painel com documentos cuja data de modificação na fonte é posterior ao `indexed_at` dos chunks, com tempo de divergência em dias. Crítico para PROC-042 e SLA-2024 — documentos que geram cálculos e compromissos contratuais.

**Por que as três camadas são necessárias:**

| Camada | Cobre | Não cobre |
|---|---|---|
| Webhook (prevenção) | Mudanças em tempo real | Falhas do webhook, edições fora do SharePoint |
| Hash/metadado (detecção) | O que o webhook perdeu | Janela até a próxima auditoria |
| Aviso inline (mitigação) | Torna o risco visível ao usuário | Não impede resposta desatualizada de ser servida |

---

### Iteração 8 — Métricas de Qualidade e Desempenho

**Problema levantado:**
Com tudo implementado em ambiente de teste, como medir a qualidade (critérios de acerto/erro) e o desempenho (tempo de resposta)?

**Análise:**

**Avaliação de qualidade — framework RAGAS**

| Métrica | O que mede | Modo de falha detectado |
|---|---|---|
| **Faithfulness** | Fatos da resposta suportados pelos chunks? | Alucinação — LLM inventou informação |
| **Answer Relevancy** | A resposta responde à pergunta? | Resposta correta mas fora do ponto |
| **Context Precision** | Os chunks recuperados eram relevantes? | Retrieval trouxe ruído |
| **Context Recall** | O retrieval trouxe todos os chunks necessários? | Retrieval deixou informação crítica de fora |

Para a NovaTech, **Faithfulness** e **Context Recall** são as métricas mais críticas: a primeira detecta multiplicadores de frete inventados, a segunda detecta ausência da seção de exceções numa pergunta sobre devolução de carga perigosa.

**Dataset de ground truth — casos prioritários:**

| Pergunta | Resposta esperada | Modo de falha a detectar |
|---|---|---|
| "Qual o prazo de devolução?" | 7 dias úteis (POL-001-A) | Prazo inventado ou errado |
| "Cliente diz que é Platinum. Qual o SLA?" | Tier não existe — orientar Gold/Silver/Standard | Alucinação de SLA para tier inexistente |
| "Qual o multiplicador para o Nordeste?" | 1.5 (PROC-042-v2-B) | Usar 1.4 da v1 |
| "Frete para 300kg para Salvador?" | Informação não disponível na base | Qualquer número inventado |
| "Carga perigosa pode ser devolvida?" | Não pelo processo padrão — ramal 4500 | Confundir exceção com regra geral |
| "Qual o prazo adicional para frete especial?" | +3 dias úteis (PROC-042-v2-C) | Usar +2 da v1 |

**LLM-as-Judge para respostas abertas:**

Para perguntas procedurais onde exact match não funciona, um segundo modelo avalia:
- Correção factual: dados estão corretos conforme o documento?
- Completude: cobre todos os aspectos relevantes?
- Atribuição de fonte: cita corretamente de onde veio a informação?

Ferramentas disponíveis no stack da NovaTech: **Azure AI Evaluation SDK** e **Promptflow** (nativos no Azure AI Studio).

**Avaliação de desempenho — latência por componente**

A latência de um sistema RAG é a soma de etapas encadeadas. Medir o total sem decompor não permite identificar onde otimizar:

| Componente | Latência típica |
|---|---|
| Embedding da query | 50–150ms |
| Busca vetorial (retrieval) | 100–400ms |
| Reranking (cross-encoder) | 300ms–1,5s |
| Tool calling (se cálculo) | 100–500ms |
| **Inferência do LLM** | **2–8s (dominante)** |
| **Total end-to-end** | **3–11s** |

**Métricas a monitorar:**

*Latência:*
- **P50** (mediana): experiência do usuário típico
- **P95**: 1 em 20 usuários — mais revelador que a média
- **P99**: casos extremos — identifica queries patológicas
- **TTFT** (Time to First Token): com streaming, é a métrica de percepção de velocidade

Target para NovaTech: P95 < 10s. Para substituir 12 minutos de busca manual, até 10 segundos representa ganho de ordem de magnitude.

*Operacional:*
- Taxa de timeout e erro por componente
- Chunk hit rate (chunks mais recuperados — identifica documentos críticos)
- No-coverage rate (% de queries sem chunks relevantes — detecta gaps de documentação)

**Instrumentação recomendada — trace estruturado por query:**

```json
{
  "query_id": "uuid",
  "timestamp": "2024-06-03T10:42:00Z",
  "latency_ms": {
    "embedding": 87,
    "retrieval": 210,
    "reranking": 640,
    "tool_calling": 180,
    "llm_inference": 4300,
    "total": 5417
  },
  "chunks_retrieved": 15,
  "chunks_after_rerank": 6,
  "ragas_faithfulness": 0.94,
  "source_docs": ["POL-001", "PROC-042-v2"],
  "had_contradiction": false,
  "had_no_coverage": false
}
```

Esse trace alimenta tanto o dashboard de latência quanto o pipeline de avaliação contínua — cada query em produção vira dado de monitoramento, não apenas as queries do dataset de teste.

**Sequência de validação no ambiente de teste:**

1. Rodar dataset de ground truth com RAGAS → baseline de qualidade antes do go-live
2. Medir latência por componente com 50–100 queries simultâneas → identificar gargalo
3. Executar os casos de armadilha do Anexo B → verificar se os modos de falha críticos estão controlados
4. Definir thresholds de alerta para produção:
   - Faithfulness < 0,85 → revisão da base e do system prompt
   - P95 > 12s → otimização de reranking ou chunk size
   - No-coverage rate > 15% → gap de documentação a endereçar

---

## Arquitetura Final Consolidada

```
┌─────────────────────────────────────────────────────────────┐
│                        INGESTÃO                             │
│                                                             │
│  SharePoint / Confluence / OneDrive                         │
│       │                                                     │
│       ├─ Webhook (Graph API) → Azure Function               │
│       │                                                     │
│       ▼                                                     │
│  Azure Document Intelligence                                │
│  (OCR + extração estruturada de tabelas)                    │
│       │                                                     │
│       ▼                                                     │
│  Chunking diferenciado por tipo de conteúdo                 │
│  + Metadados: doc_id, version, date, tier, hash             │
│       │                                                     │
│       ├─ Índice FORMAL (POL, PROC, SLA)                     │
│       └─ Índice INFORMAL (FAQ)                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        RETRIEVAL                            │
│                                                             │
│  Query do atendente                                         │
│       │                                                     │
│       ├─ Semantic Router → intent: calculation?             │
│       │       └─ Sim → Serviço de cálculo (Tool Calling)    │
│       │                                                     │
│       ▼  intent: lookup / procedural                        │
│  Query Decomposition (multi-domínio)                        │
│       │                                                     │
│       ▼                                                     │
│  Busca vetorial: Índice FORMAL → top-15 chunks              │
│  (fallback: Índice INFORMAL se cobertura insuficiente)      │
│       │                                                     │
│       ▼                                                     │
│  Filtro de versão (preferência por data mais recente)       │
│       │                                                     │
│       ▼                                                     │
│  Reranking → top-6 chunks (score mínimo de corte)           │
│       │                                                     │
│       └─ Score abaixo do mínimo → resposta de "sem cobertura"│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXT ASSEMBLY                         │
│                                                             │
│  [System prompt ~2K] + [Histórico ~1,5K] + [Pergunta ~300]  │
│  + [Chunk 1 — maior relevância] ← posição inicial           │
│  + [Chunks 2–6 — relevância decrescente]                    │
│  + [Aviso de staleness se indexed_at > 35 dias]             │
│                                                             │
│  Budget total: ~7.300–9.300 tokens                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                          LLM                                │
│                                                             │
│  System prompt instrui:                                     │
│  - Citar fonte obrigatoriamente em toda resposta            │
│  - Sinalizar contradição explicitamente ao usuário          │
│  - Nunca extrapolar para perguntas sem cobertura            │
│  - Nunca realizar cálculos aritméticos (delegar à tool)     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     MONITORAMENTO                           │
│                                                             │
│  Por query: trace com latência por componente               │
│  Diário: job de auditoria de staleness (hash + metadado)    │
│  Contínuo: RAGAS (faithfulness, recall, precision)          │
│  Dashboard: divergência fonte↔índice, no-coverage rate      │
└─────────────────────────────────────────────────────────────┘
```

---

## Matriz de Riscos

| Risco | Probabilidade | Impacto | Mitigação | Residual |
|---|---|---|---|---|
| Resposta com multiplicador da versão errada | Alta | Alto — cálculo de frete incorreto | Metadados de versão + filtro por data + tool calling | Baixo |
| FAQ citado como política oficial | Alta | Alto — informação não validada com alta confiança | Índices separados por tier | Baixo |
| Alucinação para tier "Platinum" | Média | Médio — confusão do cliente | Score mínimo + instrução no system prompt | Baixo |
| Fluxograma inacessível na base | Alta | Alto — procedimento crítico ausente | Conversão manual mapeada no escopo | Médio |
| Staleness silencioso pós-atualização | Alta | Alto — resposta coerente mas desatualizada | Webhook + hash audit + aviso inline | Baixo |
| LLM realizando cálculo autônomo | Média | Alto — erro aritmético invisível | Tool calling + pré-computação de grade | Baixo |
| Custo de manutenção não mapeado | Média | Alto — surpresa orçamentária pós-go-live | Mapear esforço recorrente no escopo | Baixo |
| Pergunta sem cobertura gerando extrapolação | Média | Alto — resposta inventada com aparência factual | Threshold de score + instrução de recusa | Baixo |

---

## Recomendações para o Go-Live

**Antes do go-live:**
1. Executar dataset de ground truth completo com RAGAS — Faithfulness mínimo de 0,85 em todos os casos críticos
2. Validar os seis casos de armadilha do Anexo B (Platinum, carga perigosa, PROC-042 versão, frete < 500kg, fluxograma, FAQ como fonte crítica)
3. Medir latência P95 sob carga simulada — target < 10 segundos
4. Confirmar com a NovaTech o processo de deprecação de versões antes da ingestão inicial
5. Mapear e inventariar todos os documentos com fluxogramas — estimar esforço de conversão

**Após o go-live:**
1. Dashboard de divergência fonte↔índice em operação desde o primeiro dia
2. Revisão quinzenal dos traces de no-coverage para identificar gaps de documentação emergentes
3. Reunião mensal com as três áreas da NovaTech (Operações, Compliance, Comercial) para alinhamento sobre documentos atualizados no ciclo anterior
