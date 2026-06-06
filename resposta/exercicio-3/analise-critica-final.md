## Resultado da verificação — Exercício 3

Mapeamento de chunks: POL-001-A = Seção 3.1, POL-001-B = Seção 3.2, POL-001-C = Seção 3.3, FAQ-03 = Item 3, FAQ-38 = Item 38, PROC-042v2-B = Seção 2.1 (v2), PROC-042-B = Seção 2.1 (v1).

---

### [p1.md](resposta/exercicio-3/p1.md) — "Qual o prazo de devolução?" — ⚠️ PARCIAL

| Gabarito | Chunk | Recuperado? |
|----------|-------|-------------|
| **DEVE** | POL-001-A (Seção 3.1 — Prazo geral) | ✅ score 3.65 |
| **DEVE** | POL-001-B (Seção 3.2 — Exceções) | ❌ ausente |
| **PODE** | POL-001-C (Seção 3.3 — Procedimento) | ✅ score -1.53 |
| — | FAQ-38 (carga danificada) | ⚠️ ruído |

**Problema:** POL-001-B (exceções ao prazo, incluindo carga perigosa) é obrigatório mas não foi recuperado. Isso faria o modelo responder apenas o prazo geral sem informar as exceções relevantes.

---

### [p2.md](resposta/exercicio-3/p2.md) — "Posso devolver carga perigosa?" — ✅ OK

| Gabarito | Chunk | Recuperado? |
|----------|-------|-------------|
| **DEVE** | POL-001-B (Seção 3.2 — Exceções) | ✅ score 2.69 |
| **PODE** | FAQ-03 (Item 3 — carga perigosa) | ✅ score 7.60 |
| **PODE** | POL-001-A | ❌ não veio |
| — | FAQ-38 | ⚠️ ruído (score baixo) |

O chunk obrigatório foi recuperado. FAQ-03 veio com score mais alto que o próprio POL-001-B, o que é aceitável pois ele estava no "pode aparecer". Resposta correta.

---

### [p3.md](resposta/exercicio-3/p3.md) — "Frete para 300kg para Salvador?" — ✅ OK

| Gabarito | Chunk | Recuperado? |
|----------|-------|-------------|
| **DEVE** | Nenhum (caso não documentado) | — |
| **PODE** | PROC-042v2-B (parcialmente relevante) | ✅ score -4.46 |
| — | PROC-042-B (v1 — versão antiga) | ⚠️ esperado como possível ruído |

Todos os scores são negativos, indicando baixa relevância — comportamento correto. A resposta identificou corretamente que 300kg está fora do intervalo documentado (< 500kg) e escalou ao supervisor.

---

### [p4.md](resposta/exercicio-3/p4.md) — "Qual o multiplicador para o Sudeste?" — ✅ OK

| Gabarito | Chunk | Recuperado? |
|----------|-------|-------------|
| **DEVE** | PROC-042v2-B (multiplicadores v2) | ✅ score 0.35 |
| **PODE** | PROC-042-B (v1 — contradição 1.0 vs 1.1) | ✅ score 0.63 |

Único ponto de atenção: a v1 ficou com score *ligeiramente maior* que a v2. O modelo seguiu corretamente a regra de preferir a versão mais recente, detectou o conflito e alertou sobre as disposições transitórias.

---

### [p5.md](resposta/exercicio-3/p5.md) — "O que acontece com carga danificada?" — ✅ OK

| Gabarito | Chunk | Recuperado? |
|----------|-------|-------------|
| **DEVE** | FAQ-38 (Item 38 — carga danificada) | ✅ score -0.67 |
| **PODE** | Nenhum documento formal | — |
| — | SLA-2024 Seção 3 (incidente crítico) | ⚠️ ruído |
| — | POL-001 Seção 3.4 (devoluções parciais) | ⚠️ ruído |

FAQ-38 recuperado corretamente. Os chunks de ruído têm scores baixíssimos e não influenciaram a resposta.

---

## Resumo geral

| Arquivo | Pergunta | Resultado |
|---------|----------|-----------|
| p1.md | Prazo de devolução | ⚠️ Parcial — faltou POL-001-B (exceções) |
| p2.md | Carga perigosa | ✅ Correto |
| p3.md | 300kg para Salvador | ✅ Correto (caso não documentado identificado) |
| p4.md | Multiplicador Sudeste | ✅ Correto (conflito detectado e tratado) |
| p5.md | Carga danificada | ✅ Correto |

**4 de 5 perguntas atenderam ao gabarito.** O único problema está em `p1.md`, onde o chunk POL-001-B (que lista as exceções ao prazo geral) não foi recuperado — o que poderia causar resposta incompleta se o usuário tivesse carga em alguma das categorias excepcionadas.