"""
Offline indexing pipeline.

Parses documentation, chunks text, generates embeddings,
and indexes them into a local Qdrant vector database.
"""

from code.ingest import load_pdf_documents
from code.embeddings import EmbeddingModel
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid

# print("Indexing script started") #Its a safety net...if you run this script and nothing happens, then this will help you to debug.

COLLECTION_NAME = "aws-org-docs"

chunks = load_pdf_documents()
texts = [c["text"] for c in chunks]

embedder = EmbeddingModel()
embeddings = embedder.embed(texts)

client = QdrantClient(host="localhost", port=6333)
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=embeddings.shape[1],
            distance=Distance.COSINE,
        ),
    )

points = []
for emb, chunk in zip(embeddings, chunks):
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),
            payload={
                **chunk["metadata"],
                "text": chunk["text"],
            },
        )
    )

UPSERT_BATCH_SIZE = 64

for i in range(0, len(points), UPSERT_BATCH_SIZE):
    batch = points[i : i + UPSERT_BATCH_SIZE]
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=batch,
    )
    print(f"Upserted {i + len(batch)} / {len(points)} points")


print(f"Indexed {len(points)} chunks into Qdrant")

# print("Indexing script finished") #Its a safety net...Same as the one above.
