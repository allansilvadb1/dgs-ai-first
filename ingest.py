import os
import re
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
    doc_meta = {"versao": "", "ultima_atualizacao": "", "responsavel": "", "classificacao": ""}

    meta_fields = {
        "**Versão:**": "versao",
        "**Última atualização:**": "ultima_atualizacao",
        "**Data de emissão:**": "ultima_atualizacao",
        "**Responsável:**": "responsavel",
        "**Classificação:**": "classificacao",
        "**Status:**": "classificacao",
    }

    # heading_stack[level] = title — tracks the active heading at each depth
    heading_stack = {}
    current_level = None
    current_title = ""
    current_lines = []

    def flush_chunk():
        text = "\n".join(current_lines).strip()
        if not text or not current_title:
            return
        path_parts = [heading_stack[l] for l in sorted(heading_stack) if 2 <= l <= current_level]
        section_path = " > ".join(path_parts) if path_parts else current_title
        parent = heading_stack.get(current_level - 1, "")
        chunks.append({
            "id": f"{filename}::{section_path}",
            "text": f"{section_path}\n{text}",
            "source": filename,
            "section": current_title,
            "parent_section": parent,
            "section_path": section_path,
            "heading_level": current_level,
            **doc_meta,
        })
        current_lines.clear()

    for line in lines:
        for prefix, key in meta_fields.items():
            if line.startswith(prefix):
                doc_meta[key] = line[len(prefix):].strip()
                break

        # Match headings at level 2+ (skip the document title at level 1)
        m = re.match(r'^(#{2,6})\s+(.*)', line)
        if m:
            flush_chunk()
            level = len(m.group(1))
            title = m.group(2).strip()
            # Invalidate all headings at this level and deeper
            for l in [l for l in heading_stack if l >= level]:
                del heading_stack[l]
            heading_stack[level] = title
            current_level = level
            current_title = title
        else:
            current_lines.append(line)

    flush_chunk()

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
            "parent_section": c["parent_section"],
            "section_path": c["section_path"],
            "heading_level": c["heading_level"],
            "versao": c["versao"],
            "ultima_atualizacao": c["ultima_atualizacao"],
            "responsavel": c["responsavel"],
            "classificacao": c["classificacao"],
        } for c in all_chunks],
    )

    print("\nIngestão concluída.")


if __name__ == "__main__":
    main()
