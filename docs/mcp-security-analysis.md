# MCP Security Analysis — NovaTech Assistant

> Análise de riscos do setup local de MCP servers configurado em `.mcp/mcp.json`.
> Contexto: ambiente de desenvolvimento local, sem serviços externos pagos.

---

## Risco 1 — `filesystem` server não suporta exclusões de arquivos

**Descrição:**
O `@modelcontextprotocol/server-filesystem` aceita apenas diretórios como argumentos e expõe **todo o conteúdo** dentro deles, sem suporte a exclusões por arquivo ou padrão glob. Qualquer arquivo sensível dentro de um diretório exposto fica acessível ao agente.

**Exemplo concreto:**
O server `filesystem-rw` expõe `./src`. Se um arquivo `.env` ou `config.ts` com credenciais hardcoded existir em `./src`, o agente pode lê-lo (ou modificá-lo) sem nenhum gate.

**Impacto:** Exposição de segredos (API keys, connection strings) ao agente de IA; risco de vazamento via outputs gerados pelo agente.

**Mitigações:**
- Manter segredos **fora** dos diretórios expostos — `.env` deve ficar na raiz do repositório (não dentro de `./src`), e nunca ser comitado (`.gitignore`).
- Usar variáveis de ambiente injetadas pelo sistema operacional em vez de arquivos `.env` dentro dos escopos MCP.
- Subdividir escopos quando possível: expor `./src/functions` e `./src/services` individualmente, em vez de `./src` inteiro.

---

## Risco 2 — Agente prefere ferramentas built-in e contorna o least privilege

**Descrição:**
O Claude Code possui ferramentas nativas (`Read`, `Bash`) com escopo irrestrito sobre o sistema de arquivos local. Sem instrução explícita no prompt, o agente escolhe essas ferramentas em vez dos MCP servers — ignorando os escopos mínimos definidos no `.mcp/mcp.json`.

**Exemplo concreto:**
Um prompt genérico como *"liste os arquivos em docs/novatech/"* resulta em uso do `Read` built-in, que acessa qualquer caminho do sistema, não apenas os diretórios autorizados pelo `filesystem-ro`. O least privilege configurado é contornado silenciosamente.

**Impacto:** O modelo de segurança baseado em escopos MCP só funciona quando o agente é forçado a usá-los — prompts genéricos anulam a separação `rw` vs `ro`.

**Mitigações:**
- Sempre referenciar o server explicitamente nos prompts: *"Use o MCP server filesystem-ro para..."*
- Registrar no `AGENTS.md` do projeto a regra: *"Para leitura de docs/novatech/ e data/retrieval-corpus/, sempre usar filesystem-ro. Para escrita em src/, specs/ e skills/, sempre usar filesystem-rw."*
- Desabilitar ou restringir ferramentas built-in via configuração de permissões do Claude Code quando o controle de escopo for crítico.

---

## Risco 3 — Server com escrita habilitada permite alteração de arquivos sem gate de revisão

**Descrição:**
O server `filesystem-rw` tem permissão de escrita sobre `./src`, `./specs` e `./skills`. Um agente mal instruído (ou um prompt ambíguo) pode sobrescrever código de produção, specs aprovadas ou skills do projeto sem nenhuma revisão humana no caminho.

**Exemplo concreto:**
Um prompt como *"refatore o handler.ts para simplificar"* pode resultar na sobrescrita do arquivo antes de qualquer revisão, perdendo lógica implementada ou introduzindo bugs silenciosamente.

**Impacto:** Perda de trabalho; introdução de regressões sem rastreabilidade; violação do validation gate "Code → Merge" definido no processo do projeto.

**Mitigações:**
- Usar branches git antes de qualquer sessão com escrita habilitada — toda alteração fica rastreada e reversível via `git diff` / `git checkout`.
- Adotar o padrão de revisão obrigatória pós-geração: o agente gera, o desenvolvedor revisa o diff antes de commitar (`git add -p` para staging seletivo).
- Documentar no `AGENTS.md`: *"Nunca commitar código gerado por agente sem revisão humana do diff completo."*

---

## Resumo

| # | Risco | Impacto | Mitigação principal |
|---|-------|---------|---------------------|
| 1 | `filesystem` expõe secrets dentro do escopo | Vazamento de credenciais | Secrets fora dos diretórios expostos |
| 2 | Agente usa ferramentas built-in em vez do MCP | Least privilege contornado silenciosamente | Referenciar server explicitamente nos prompts |
| 3 | Escrita sem gate de revisão | Sobrescrita de código sem rastreabilidade | Branch git + revisão do diff antes de commitar |
