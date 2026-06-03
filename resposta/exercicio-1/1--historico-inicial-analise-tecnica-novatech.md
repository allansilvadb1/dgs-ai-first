# Sessão de Análise Técnica — Assistente de IA NovaTech
**Data:** 2026-06-03  
**Participantes:** Allan Silva + Claude (Sonnet 4.6)  
**Branch:** cenario-1

---

## Contexto Inicial

**Allan:** Claude, vamos realizar uma análise de construção de um assistente de IA para a NovaTech. Aqui iremos analisar do ponto de vista do desenvolvedor alguns critérios que foi passado para nós. Dê uma olhada nos arquivos que temos neste repositório para tomar nota do assunto, em seguida trarei alguns tópicos para analisarmos juntos.

**Claude:** Leitura completa. Aqui está o panorama do que temos no repositório:

**Cenário:** A NovaTech (empresa de logística) contratou a DB1 para construir um assistente de IA para o time de atendimento. O objetivo é reduzir o tempo de busca de informações de **12 minutos para menos de 2 minutos por chamado**.

**Base documental simulada (5 documentos):**
- POL-001 — Política de devolução de mercadorias (v3.1 — documento formal)
- PROC-042 v1 — Cálculo de frete especial (v1.0 — possivelmente obsoleto)
- PROC-042 v2 — Cálculo de frete especial revisado (v2.0 — coexiste com o anterior sem hierarquia clara)
- SLA-2024 — Tabela de SLA por tier de cliente (Gold, Silver, Standard)
- FAQ-Atendimento — FAQ informal, sem validação de Compliance

**Problemas críticos já identificados no material:**
1. **Contradição de versões:** PROC-042 v1 e v2 têm multiplicadores regionais, fatores de peso e prazos diferentes — nenhuma está marcada como obsoleta
2. **Fonte não confiável misturada:** O FAQ é informal e pode contaminar respostas do assistente com informações desatualizadas ou inventadas
3. **Gaps documentais:** Não existe documento formal sobre carga danificada em trânsito, seguro de carga ou frete padrão abaixo de 500kg
4. **Risco de alucinação:** O assistente pode inventar SLAs para tier "Platinum" (que não existe) se o retrieval falhar

---

## Pergunta 1 — Viabilidade Técnica e Desafios do Pipeline de RAG

**Allan:** O Tech Lead nos pediu que avalie a viabilidade técnica do assistente considerando as características da documentação da NovaTech e o impacto do gerenciamento de contexto na arquitetura.

- Informações técnicas adicionais: *"Os PDFs do SharePoint incluem documentos com tabelas complexas (tabelas de frete com 15+ colunas), fluxogramas embutidos como imagens, e alguns documentos escaneados (OCR necessário). A wiki do Confluence tem links internos entre páginas e usa macros customizadas. As planilhas têm fórmulas interdependentes."*
- Conceito de context engineering aplicado a RAG: *"O contexto que o LLM recebe a cada pergunta é limitado pela janela de contexto do modelo. A qualidade da resposta depende de: quais chunks são selecionados (relevância), quantos chunks cabem no contexto (orçamento de atenção), onde ficam posicionados no prompt (informação no meio de contextos longos é 'esquecida' — o efeito 'lost in the middle'), e o que mais está no contexto competindo por atenção (system prompt, histórico de conversa, instruções)."*

Com base nisso, vamos elencar os desafios do pipeline de RAG e como isso afeta a qualidade das respostas, e qual estratégia para tratá-los.

**Claude:**

### 1. Ingestão e Pré-processamento

**Problema: Fontes heterogêneas com formatos difíceis**

| Fonte | Problema concreto | Risco |
|---|---|---|
| PDFs com tabelas de 15+ colunas | Chunking por token quebra a tabela no meio de uma linha | LLM recebe fragmento de tabela sem cabeçalho, não consegue interpretar o dado |
| PDFs escaneados | OCR necessário; qualidade variável | Chunk com OCR ruim vira ruído indexado — a busca semântica vai recuperar lixo com alta confiança |
| Fluxogramas embutidos como imagem | São ignorados no pipeline de texto puro | Procedimentos que só existem como fluxograma somem da base do assistente |
| Confluence com macros customizadas | A exportação em texto plano não renderiza as macros | Conteúdo crítico pode aparecer como `{macro:name=...}` no índice |
| Planilhas com fórmulas interdependentes | Fórmulas não avaliam durante ingestão; os valores ficam fora da base | Assistente não sabe o resultado real — ex: cálculo de frete base do mês |

**Estratégia:**
- Usar **Azure Document Intelligence** para extração estruturada de tabelas — preserva a estrutura linha/coluna como markdown
- Tabelas complexas devem ser indexadas como **chunks de tabela inteira** com cabeçalho replicado, não fatiadas por tamanho de token
- Fluxogramas: mapear quais procedimentos dependem de imagem e criar documentos textuais equivalentes
- Planilhas: pré-computar os valores e indexar um documento derivado com os resultados — não as fórmulas

### 2. Qualidade da Base — Contradições e Gaps

**Problema: Documentos conflitantes coexistindo no mesmo índice**

Para uma query como *"qual o multiplicador para o Nordeste?"*, o retrieval pode retornar:
- `PROC-042-B`: Nordeste = 1.4 (v1)
- `PROC-042v2-B`: Nordeste = 1.5 (v2)

O LLM recebe os dois no contexto e tem duas saídas possíveis — ambas ruins: escolhe um arbitrariamente sem avisar o usuário, ou cita os dois como se fossem igualmente válidos.

**Estratégia — curto prazo:**
- Enriquecer cada chunk com **metadados de versão e data** (`doc_id`, `version`, `date`, `status: formal|informal`)
- Na camada de retrieval, aplicar **filtro de preferência por data mais recente** quando dois chunks do mesmo procedimento são retornados
- Instruir o system prompt a sinalizar explicitamente a contradição ao usuário

**Estratégia — médio prazo:**
- Estabelecer com a NovaTech um processo de **deprecação explícita**: documentos substituídos recebem metadado `status: deprecated` e são excluídos do índice ativo

**Problema: FAQ informal misturado com documentos normativos**

**Estratégia:**
- Criar **coleções (índices) separadas** por tier de confiança: `formal` (POL, PROC, SLA) e `informal` (FAQ)
- O pipeline de recuperação prioriza a coleção `formal`; só busca em `informal` se não encontrar cobertura suficiente
- O system prompt instrui o LLM a sinalizar a fonte na resposta: *"Conforme a POL-001..."* vs *"De acordo com o FAQ interno (não validado)..."*

### 3. Context Engineering — Orçamento de Atenção

**Problema: Competição por tokens no contexto**

```
[System Prompt] + [Histórico de Conversa] + [Chunks Recuperados] + [Pergunta] = Janela Total
```

**Estratégia:**
- Definir um **orçamento explícito por componente**: máximo 60% da janela para chunks, 20% para system prompt, 20% para histórico + pergunta
- Usar **reranking** para selecionar apenas os 3–4 chunks mais relevantes após o retrieval inicial de 10–15
- Para histórico de conversa: manter apenas as últimas N trocas relevantes

**Problema: "Lost in the Middle"**

Se o chunk mais relevante cai no meio de vários chunks, o modelo tende a sub-pesar essa informação.

**Estratégia:**
- Posicionar o chunk de maior relevância (score mais alto do reranker) **no início do contexto**
- Layout do contexto no prompt: `[Chunk mais relevante] → [2º mais relevante] → ... → [Menos relevante]`

### 4. Retrieval — Casos Problemáticos Específicos

**Query sem cobertura documental:** Para pergunta *"qual o frete para 300kg para Salvador?"* (frete abaixo de 500kg não está documentado), incluir no system prompt instrução explícita de que o assistente deve informar que a informação não está disponível — nunca extrapolar.

**Query multi-domínio:** Usar **query decomposition**: quebrar a pergunta em sub-queries antes do retrieval para garantir cobertura de múltiplos domínios.

### Arquitetura Recomendada

```
Ingestão
  └─ Azure Document Intelligence (tabelas, OCR)
  └─ Chunking semântico com metadados (doc_id, version, date, tier: formal|informal)
  └─ Índices separados por tier de confiança

Retrieval
  └─ Query decomposition para perguntas multi-domínio
  └─ Busca em índice formal primeiro; informal como fallback
  └─ Reranking (top-15 → top-4) com score mínimo de corte
  └─ Filtro de versão por data mais recente

Context Assembly
  └─ Orçamento de tokens por componente
  └─ Posicionamento: chunk mais relevante primeiro
  └─ Metadado de fonte embutido em cada chunk

LLM
  └─ System prompt com regras de citação de fonte, sinalização de
     contradição, e proibição de extrapolação
```

---

## Pergunta 2 — Estratégias de Ingestão que Requerem Intervenção Manual

**Allan:** Das estratégias de ingestão, recapitule aquelas que precisaremos de intervenção manual (do desenvolvedor ou do cliente) para tornar o documento compreensível no processo.

**Claude:**

Das estratégias levantadas, estas são as que dependem de intervenção humana — separadas por quem executa:

### Intervenção do Desenvolvedor

**Fluxogramas embutidos como imagem**

O pipeline de texto simplesmente ignora a imagem. Alguém precisa ler o fluxograma e produzir um documento textual equivalente descrevendo o procedimento passo a passo (PlantUML, Mermaid, ou texto estruturado). Isso é trabalho de mapeamento manual feito uma vez por documento afetado — e precisa ser **refeito toda vez que o fluxograma original for atualizado**.

**Planilhas com fórmulas interdependentes**

As fórmulas não avaliam durante a ingestão. O desenvolvedor precisa abrir cada planilha, identificar quais valores calculados são relevantes para o atendimento, e produzir um documento derivado com os resultados já computados.

Exemplo: em vez de indexar `=B3*C3*fator_regional`, indexar:
> _"Frete para 600kg no Nordeste = R$ 1.847,00 (referência: tabela frete-base-2024-05)"_

### Intervenção do Cliente (NovaTech)

**Macros customizadas do Confluence**

A exportação do Confluence em texto plano não renderiza as macros — o conteúdo aparece como código de macro. A NovaTech precisa revisar cada página afetada e converter o conteúdo das macros para texto estático, ou o desenvolvedor usa a API do Confluence para exportar o HTML renderizado (mais escalável, mas ainda pode exigir validação do cliente para confirmar que o conteúdo renderizado está correto).

**Governança de versões conflitantes (PROC-042 v1 e v2)**

A estratégia de filtrar por data mais recente resolve o sintoma tecnicamente, mas o problema de raiz só é resolvido se a NovaTech estabelecer um processo de deprecação: quem aprova a nova versão também marca a anterior como obsoleta no SharePoint. Sem isso, cada ciclo de atualização mensal pode introduzir novos pares conflitantes — e o desenvolvedor vai precisar identificá-los e tratá-los manualmente em cada ciclo de ingestão.

### Por que isso importa para o escopo

Essas quatro situações têm impacto direto no planejamento dos 3 meses de discovery + desenvolvimento + go-live. Fluxogramas e planilhas requerem esforço recorrente toda vez que os documentos são atualizados — o que, no caso da NovaTech, acontece mensalmente. Se isso não for mapeado no escopo, o custo de manutenção vai aparecer como surpresa após o go-live.

---

## Pergunta 3 — Estimativa do Tamanho da Base de Tokens

**Allan:** Agora vamos olhar para os documentos disponibilizados (pdf, Wiki, planilhas). Vamos estimar o tamanho da base de tokens considerando ~800 documentos PDF (média de 10 páginas cada), ~400 páginas wiki (média de 1.500 palavras cada), e ~50 planilhas. Vamos usar ~0.75 palavras por token. De antemão já sabemos: impossível ter todo o conteúdo em contexto, existem PDF com imagem que precisa ser processado separadamente, existem fluxogramas que precisam ser pré-processados, e páginas da wiki que possuem macros e links para outras páginas.

**Claude:**

### Cálculo por fonte

**PDFs**
```
800 documentos × 10 páginas = 8.000 páginas
8.000 páginas × 300 palavras/página = 2.400.000 palavras
2.400.000 ÷ 0,75 = ~3.200.000 tokens (3,2M)
```
> 300 palavras/página é a estimativa padrão para documentos corporativos com texto corrido, tabelas e cabeçalhos.

**Wiki Confluence**
```
400 páginas × 1.500 palavras = 600.000 palavras
600.000 ÷ 0,75 = ~800.000 tokens (800K)
```

**Planilhas** (estimativa após serialização dos valores calculados)
```
50 planilhas × ~2.000 palavras = 100.000 palavras
100.000 ÷ 0,75 = ~133.000 tokens (133K)
```

### Consolidação

| Fonte | Palavras | Tokens |
|---|---|---|
| PDFs (800 docs) | 2.400.000 | **3.200.000** |
| Wiki Confluence (400 pág.) | 600.000 | **800.000** |
| Planilhas (50) | 100.000 | **133.000** |
| **Total** | **3.100.000** | **~4.133.000** |

### O que essa estimativa significa na prática

**Nenhuma janela de contexto atual comporta essa base.**

| Modelo | Janela máxima | % da base que cabe |
|---|---|---|
| Claude Sonnet / GPT-4o | 128K–200K tokens | ~4,8% |
| Gemini 1.5 Pro | 1M tokens | ~24% |
| **Base NovaTech** | **4,1M tokens** | — |

Mesmo o modelo com maior janela disponível hoje comporta apenas um quarto da base. RAG não é uma escolha arquitetural aqui — é um requisito estrutural.

### Impacto do conteúdo que precisa de pré-processamento

- **Fluxogramas:** conversão para texto tende a ser mais verbosa. Se 10–15% dos documentos têm fluxogramas, acréscimo de 100K–200K tokens na base
- **Macros do Confluence:** após resolução via API, o volume da wiki pode crescer 10–20%
- **Planilhas pré-computadas:** documentos derivados tendem a ser mais extensos que a planilha bruta serializada

**Estimativa ajustada pós-pré-processamento: ~4,5M–4,8M tokens.**

---

## Pergunta 4 — Orçamento de Contexto e o Problema dos 252 Chunks

**Allan:** Certo, agora vamos ver do ponto de vista de orçamento do contexto. Dado que o GPT-4o tem 128K tokens de janela e o system prompt + instruções consomem ~2K tokens, teríamos 252 chunks de ~500 tokens por query. Como ficamos nesta situação?

**Claude:**

O cálculo está certo matematicamente. Mas 252 chunks por query é um cenário de degradação, não de capacidade.

### O orçamento real de contexto

```
128.000 tokens (janela total)
─────────────────────────────────────────
  - 2.000  system prompt + instruções
  - 1.500  histórico de conversa (últimas 3-5 trocas)
  -   300  pergunta do atendente + metadados
─────────────────────────────────────────
= 124.200 tokens "disponíveis" para chunks
÷ 500 tokens por chunk
= ~248 chunks
```

Na teoria: ~248–252 chunks cabem. Na prática: isso é o pior cenário possível.

### Por que 252 chunks é prejudicial

**Lost in the Middle em escala** (Liu et al., 2023):
```
Chunk 1–5      → modelo presta atenção ✓
Chunk 6–246    → zona de degradação severa ✗
Chunk 247–252  → modelo presta atenção ✓
```

**Contradições viram ruído insolúvel:** Com 252 chunks, certamente entram no contexto tanto `PROC-042-B` (Nordeste = 1.4, v1) quanto `PROC-042v2-B` (Nordeste = 1.5, v2). O modelo tem 252 fragmentos para reconciliar — a probabilidade de escolher a versão errada sem sinalizar aumenta drasticamente.

**Custo e latência:** Para ~192 queries/dia (60% de 320 chamados), o custo operacional com contexto cheio é significativamente maior que com contexto otimizado.

### Orçamento prático recomendado

| Componente | Tokens | Chunks |
|---|---|---|
| System prompt + instruções | 2.000 | — |
| Histórico de conversa | 1.500 | — |
| Pergunta + metadados | 300 | — |
| **Chunks recuperados** | **3.000–5.000** | **6–10 chunks** |
| Buffer de segurança | ~500 | — |
| **Total usado** | **~7.300–9.300** | — |

A janela grande do GPT-4o não é um convite para encher de chunks — é uma margem de segurança para conversas mais longas e contextos complexos.

### Implicação para o índice

```
4.100.000 tokens ÷ 500 tokens/chunk = ~8.200 chunks no índice total
6–10 chunks por query = 0,07%–0,12% da base acessada por pergunta
```

**A qualidade da resposta é determinada quase inteiramente pelo retrieval.** Se os 6–10 chunks recuperados forem os certos, a resposta é boa. Se trouxer um chunk de versão desatualizada do PROC-042, o LLM não tem como corrigir — o dado correto simplesmente não estará no contexto.

---

## Pergunta 5 — Estratégia de Chunking

**Allan:** Com base no que vimos até aqui recomende uma estratégia de chunking justificada pelo tipo de pergunta que o usuário fará e pelo conceito de *lost in the middle*.

**Claude:**

### Premissa

O tamanho do chunk deve ser determinado pelo **tipo de resposta que a pergunta exige**, não por um valor fixo de tokens. Chunks uniformes de 500 tokens são um ponto de partida genérico — para a NovaTech, esse tamanho único garante que nenhum tipo de pergunta seja bem atendido.

### Mapeamento: tipo de pergunta → necessidade de chunk

**Perguntas de lookup pontual**
> "Qual o prazo de devolução?" / "Qual o SLA do cliente Gold para incidente crítico?"

Precisam de um fato específico. Um chunk de 500 tokens sobre a política de devolução inteira entrega a resposta enterrada no terceiro parágrafo — que, dado o lost in the middle, pode não ser processado adequadamente pelo LLM mesmo que o chunk esteja no contexto.

**Perguntas procedurais**
> "Como abro um chamado de devolução?" / "Quais documentos preciso para frete especial acima de 3.000kg?"

Precisam de uma sequência completa de passos. Se os passos 1–3 estão num chunk e os passos 4–7 em outro, o retrieval provavelmente traz apenas um dos dois — e a resposta fica incompleta.

**Perguntas de cálculo com tabela**
> "Qual o frete para 600kg para Manaus?"

Precisam da fórmula + o valor da tabela juntos. Se a fórmula está num chunk e os multiplicadores regionais em outro, o LLM recebe metade da informação necessária.

### Chunking diferenciado por tipo de conteúdo

| Tipo de conteúdo | Tamanho | Overlap | Lógica de corte |
|---|---|---|---|
| Valores tabelados (SLA, multiplicadores, fatores de peso) | 150–250 tokens | 0 | Uma seção lógica da tabela com cabeçalho replicado |
| Passos procedurais (listas numeradas) | 300–500 tokens | 50 tokens | Limite de etapa, nunca no meio de um passo |
| Regras + exceções (POL-001) | 250–400 tokens | 75 tokens | Regra e suas exceções no mesmo chunk |
| Itens de FAQ | 100–200 tokens | 0 | Um par pergunta/resposta por chunk |
| Texto narrativo (contexto, definições) | 300–400 tokens | 75 tokens | Limite de parágrafo |

### O cabeçalho de contexto: mitigação do lost in the middle

Chunk bem construído para a NovaTech não começa diretamente com o conteúdo — ele abre com uma linha de contexto embutida no texto do chunk:

```
[POL-001 v3.1 | Seção 3.1 | Prazo de devolução]
O cliente pode solicitar devolução em até 7 dias úteis após
a data de recebimento confirmada no sistema de tracking...
```

**Por que funciona:** quando esse chunk está na posição 5 de 8 no contexto, o LLM lê a linha de cabeçalho e já sabe que está processando a política oficial de prazo. Sem o cabeçalho, um chunk na posição central é texto sem atribuição — o modelo tende a sub-pesar informação que não consegue ancorar numa fonte. O cabeçalho transforma contexto anônimo em fonte identificada.

### Aplicação aos documentos da NovaTech

**SLA-2024 — não deve ser um chunk único.** Cada seção lógica vira um chunk separado:
- Chunk A: classificação de tiers (Gold/Silver/Standard + critérios)
- Chunk B: SLAs para chamados gerais (tabela de resposta/resolução)
- Chunk C: SLAs para incidentes críticos
- Chunk D: definição de incidente crítico
- Chunk E: penalidades por descumprimento

Pergunta *"qual o SLA do Gold para incidente crítico?"* recupera o Chunk C — 150 tokens com a resposta exata, sem ruído.

**PROC-042-v2 — fórmula e tabela de multiplicadores no mesmo chunk:**

```
[PROC-042 v2.0 | Seção 2 | Fórmula e multiplicadores regionais]
Frete = Valor base × Multiplicador regional × Fator de peso
Fatores: 1.0 (500–1.000kg) | 1.15 (1.001–3.000kg) | 1.4 (>3.000kg)
Multiplicadores: Sul 1.3 | Sudeste 1.1 | Centro-Oeste 1.4 | Nordeste 1.5 | Norte 1.8
```

Um chunk, uma unidade de cálculo completa.

**POL-001 — regra geral e exceções juntas:** A seção 3.2 (exceções ao prazo geral) não pode ser separada da seção 3.1 (regra geral). Pergunta *"carga perigosa pode ser devolvida?"* exige as duas — a regra e a exceção no mesmo chunk, para o modelo não responder afirmativamente baseado só na regra sem ver a exceção imediatamente abaixo.

### Efeito no orçamento de contexto

Com chunks menores e mais precisos, os 6–10 chunks do orçamento prático cobrem **mais domínios diferentes** por query:

```
10 chunks × 500 tokens = 5.000 tokens → 1 domínio bem coberto
10 chunks × 250 tokens = 2.500 tokens → 2–3 domínios cobertos
```

Para as perguntas multi-domínio da NovaTech — que cruzam política de devolução com frete especial, por exemplo — isso é a diferença entre uma resposta completa e uma resposta parcial.

---

## Síntese dos Riscos Críticos

| Risco | Causa | Impacto | Mitigação |
|---|---|---|---|
| Resposta com multiplicador errado | PROC-042 v1 e v2 coexistem no índice | Cálculo de frete incorreto informado ao cliente | Metadados de versão + filtro por data + system prompt de sinalização |
| Resposta baseada no FAQ como política oficial | FAQ informal no mesmo índice que documentos normativos | Informação não validada comunicada com alta confiança | Índices separados por tier de confiança |
| Resposta inventada para tier "Platinum" | Pergunta sem cobertura + modelo extrapolando | Alucinação com aparência de fato | Score mínimo de relevância + instrução no system prompt |
| Fluxograma de procedimento inacessível | Imagens não indexadas | Procedimento crítico ausente da base | Conversão manual para texto estruturado (escopo do projeto) |
| Custo de manutenção não mapeado | Atualizações mensais requerem reprocessamento manual | Surpresa orçamentária pós-go-live | Mapear esforço recorrente nos 3 meses de escopo |
