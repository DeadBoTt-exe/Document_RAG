from code.ingest import load_pdf_documents
from code.embeddings import EmbeddingModel
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid

print("Indexing script started")

COLLECTION_NAME = "aws-org-docs"

# 1. Load PDF chunks
chunks = load_pdf_documents()
texts = [c["text"] for c in chunks]

# 2. Embed once
embedder = EmbeddingModel()
embeddings = embedder.embed(texts)

# 3. Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

# 4. Create collection if missing
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=embeddings.shape[1],
            distance=Distance.COSINE,
        ),
    )

# 5. Upload vectors
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

UPSERT_BATCH_SIZE = 64  # safe on Windows

for i in range(0, len(points), UPSERT_BATCH_SIZE):
    batch = points[i : i + UPSERT_BATCH_SIZE]
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=batch,
    )
    print(f"Upserted {i + len(batch)} / {len(points)} points")


print(f"Indexed {len(points)} chunks into Qdrant")

print("Indexing script finished")
