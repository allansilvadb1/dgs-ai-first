import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

SYSTEM_PROMPT = """
# IDENTIDADE
Assistente de consulta documental da NovaTech (logística).
Responde apenas com base nos chunks fornecidos. Não é chatbot genérico.

# REGRAS
1. Citar sempre: (Fonte: DOCUMENTO, SEÇÃO)
2. Não inventar valores, prazos ou regras ausentes nos documentos.
3. Informação ausente → responder: "Não encontrei na documentação. Recomendo escalar ao supervisor."
4. Português formal.
5. Apenas o que foi perguntado. Sem conselhos não solicitados.

# CONFLITO ENTRE FONTES
Preferir versão mais recente (v2 > v1). Alertar: "Encontrei versões conflitantes. Usando a mais recente. Confirme com o supervisor."

# FORMATO
- Resposta direta (1-3 frases)
- Fonte ao final
- Alerta apenas se documentação for incompleta ou contraditória
"""

client = chromadb.HttpClient(host="localhost", port=8000)
# client.delete_collection("novatech")  # Limpa coleção para testes
collection = client.get_collection("novatech")

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
reranker = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")


def montar_prompt(pergunta, chunks):
    contexto = ""
    for i, (doc, meta) in enumerate(chunks, 1):
        contexto += f"[Trecho {i} — Fonte: {meta['source']}, Seção: {meta['section_path']}, Última Atualização: {meta['ultima_atualizacao']}]\n{doc}\n\n"

    return f"""{SYSTEM_PROMPT}

---
# DOCUMENTAÇÃO DISPONÍVEL (contexto recuperado para esta consulta)
{contexto.strip()}

---
PERGUNTA DO USUÁRIO:
{pergunta}"""


print("Digite sua pergunta (ou 'sair' para encerrar):\n")

while True:
    pergunta = input(">>> ").strip()

    if pergunta.lower() == "sair":
        break

    if not pergunta:
        continue

    vetor_pergunta = model.encode(pergunta).tolist()

    resultados = collection.query(
        query_embeddings=[vetor_pergunta],
        n_results=10
    )

    docs = resultados["documents"][0]
    metas = resultados["metadatas"][0]

    pares = [(pergunta, doc) for doc in docs]
    scores_reranker = reranker.predict(pares)

    ranking = sorted(
        zip(scores_reranker, docs, metas),
        key=lambda x: x[0],
        reverse=True
    )

    top3 = ranking[:3]
    chunks = [(doc, meta) for _, doc, meta in top3]

    print("\n--- CHUNKS RECUPERADOS (após reranking) ---")
    for score, doc, meta in top3:
        print(f"  Score: {score:.4f} | [{meta['source']}] {meta['section']}")
    print()

    prompt = montar_prompt(pergunta, chunks)

    print("--- PROMPT MONTADO (copie e cole no Claude) ---")
    print(prompt)
    print("-----------------------------------------------\n")
