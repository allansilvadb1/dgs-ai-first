# Criar e ativar virtualenv
python -m venv .venv && source .venv/bin/activate

# Instalar dependências
pip install chromadb-client sentence-transformers


**Analogia prática:**

| Papel | Ferramenta | Faz o quê |
|---|---|---|
| Traduz texto → números | sentence-transformers | Entende semântica |
| Guarda e busca números | ChromaDB | Só matemática |
| Gera resposta | Claude | Raciocina sobre o contexto |

```
"qual o prazo de entrega?" 
    → sentence-transformers → [0.12, -0.34, 0.87, ...]
    → ChromaDB compara com todos os vetores guardados
    → retorna os textos cujos vetores são matematicamente mais próximos
```

O ChromaDB não sabe que "prazo" e "deadline" são parecidos — é o sentence-transformers que já embutiu isso nos vetores antes de salvar.