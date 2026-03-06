import sys
from pathlib import Path

# add project root to Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.embeddings import get_embedding_model

model = get_embedding_model()

vec = model.embed_query("def add(a,b): return a+b")

print("Vector length:", len(vec))
print(vec[:10])