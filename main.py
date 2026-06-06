import chromadb
from sentence_transformers import SentenceTransformer

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


def montar_prompt(pergunta, chunks):
    contexto = ""
    for i, (doc, meta) in enumerate(chunks, 1):
        contexto += f"[Trecho {i} — Fonte: {meta['source']}, Seção: {meta['section']}]\n{doc}\n\n"

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
        n_results=3
    )

    chunks = list(zip(resultados["documents"][0], resultados["metadatas"][0]))

    print("\n--- CHUNKS RECUPERADOS ---")
    for doc, meta, score in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0]
    ):
        print(f"  Score: {score:.4f} | [{meta['source']}] {meta['section']}")
    print()

    prompt = montar_prompt(pergunta, chunks)

    print("--- PROMPT MONTADO (copie e cole no Claude) ---")
    print(prompt)
    print("-----------------------------------------------\n")
