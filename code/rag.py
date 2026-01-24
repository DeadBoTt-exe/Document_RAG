from typing import Dict, List
import os
import numpy as np

from dotenv import load_dotenv
import google.genai as genai
from qdrant_client import QdrantClient

from code.embeddings import EmbeddingModel

load_dotenv()


COLLECTION_NAME = "aws-org-docs"


class RAGEngine:
    def __init__(self):
        # --- Gemini setup ---
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment")

        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.5-flash"

        # --- Embedder (query-only) ---
        self.embedder = EmbeddingModel()

        # --- Qdrant client ---
        self.qdrant = QdrantClient(
            host="localhost",
            port=6333,
        )

        # Sanity check: collection must exist
        collections = [
            c.name for c in self.qdrant.get_collections().collections
        ]
        if COLLECTION_NAME not in collections:
            raise RuntimeError(
                f"Qdrant collection '{COLLECTION_NAME}' not found. "
                "Run index_documents.py first."
            )

    def ask(self, question: str, top_k: int = 5) -> Dict:
        # --- Embed query ---
        query_embedding = self.embedder.embed([question])
        query_embedding = query_embedding / np.linalg.norm(
            query_embedding, axis=1, keepdims=True
        )

        # --- Vector search ---
        search_result = self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding[0].tolist(),
            limit=top_k,
        )
        results = search_result.points

        if not results:
            return {
                "answer": "I don't know based on the documentation.",
                "sources": [],
            }

        # --- Build context ---
        context_chunks: List[str] = []
        sources = set()

        for r in results:
            payload = r.payload
            context_chunks.append(payload["text"])
            sources.add(
                f'{payload["file"]}#page-{payload["page"]}'
            )

        context = "\n\n".join(context_chunks)

        # --- Grounded prompt ---
        prompt = f"""
You are an engineering documentation assistant.
Answer ONLY using the context below.
If the answer is not present, say "I don't know based on the documentation."

Context:
{context}

Question:
{question}

Answer:
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return {
            "answer": response.text.strip(),
            "sources": sorted(sources),
        }
