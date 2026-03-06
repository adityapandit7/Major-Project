import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.embeddings import get_embedding_model
from core.vector_store import build_vector_index

docs = [
    {"name": "add", "type": "function", "content": "def add(a,b): return a+b"},
    {"name": "multiply", "type": "function", "content": "def multiply(a,b): return a*b"}
]

embedding_model = get_embedding_model()

vector_db = build_vector_index(docs, embedding_model)

results = vector_db.similarity_search("addition")

print(results)