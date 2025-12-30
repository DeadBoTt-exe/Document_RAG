from typing import Dict
import os

from dotenv import load_dotenv
import google.genai as genai

from app.embeddings import EmbeddingModel
from app.retriever import FaissRetriever
from app.ingest import load_markdown_files

load_dotenv()


class RAGEngine:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment")


        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.5-flash"
        self.embedder = EmbeddingModel()
        self.chunks = load_markdown_files()
        texts = [c["text"] for c in self.chunks]
        embeddings = self.embedder.embed(texts)
        self.retriever = FaissRetriever(
            embedding_dim=embeddings.shape[1]
        )
        self.retriever.add(embeddings, self.chunks)

    def ask(self, question: str, top_k: int = 3) -> Dict:
        query_embedding = self.embedder.embed([question])
        results = self.retriever.search(query_embedding, top_k)

        context = "\n\n".join(r["text"] for r in results)
        sources = list({
            f'{r["metadata"]["file"]}#{r["metadata"]["section"]}'
            for r in results
        })

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
            "sources": sources,
        }
