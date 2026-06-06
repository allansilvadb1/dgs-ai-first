import os
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = "anexo-a-documentos-individuais"
COLLECTION_NAME = "novatech"

def load_chunks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    lines = content.split("\n")

    chunks = []
    current_title = ""
    current_lines = []
    doc_meta = {"versao": "", "ultima_atualizacao": "", "responsavel": "", "classificacao": ""}

    meta_fields = {
        "**Versão:**": "versao",
        "**Última atualização:**": "ultima_atualizacao",
        "**Data de emissão:**": "ultima_atualizacao",
        "**Responsável:**": "responsavel",
        "**Classificação:**": "classificacao",
        "**Status:**": "classificacao",
    }

    for line in lines:
        for prefix, key in meta_fields.items():
            if line.startswith(prefix):
                doc_meta[key] = line[len(prefix):].strip()
                break

        if line.startswith("### "):
            if current_lines:
                chunks.append({
                    "id": f"{filename}::{current_title}",
                    "text": f"{current_title}\n" + "\n".join(current_lines).strip(),
                    "source": filename,
                    "section": current_title,
                    **doc_meta,
                })
            current_title = line.strip("# ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines and current_title:
        chunks.append({
            "id": f"{filename}::{current_title}",
            "text": f"{current_title}\n" + "\n".join(current_lines).strip(),
            "source": filename,
            "section": current_title,
            **doc_meta,
        })

    return chunks


def main():
    client = chromadb.HttpClient(host="localhost", port=8000)

    client.delete_collection(COLLECTION_NAME)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    all_chunks = []
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(DOCS_DIR, filename)
            chunks = load_chunks(filepath)
            all_chunks.extend(chunks)
            print(f"{filename}: {len(chunks)} chunks")

    print(f"\nTotal: {len(all_chunks)} chunks\n")

    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    collection.add(
        ids=[c["id"] for c in all_chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{
            "source": c["source"],
            "section": c["section"],
            "versao": c["versao"],
            "ultima_atualizacao": c["ultima_atualizacao"],
            "responsavel": c["responsavel"],
            "classificacao": c["classificacao"],
        } for c in all_chunks],
    )

    print("\nIngestão concluída.")


if __name__ == "__main__":
    main()
