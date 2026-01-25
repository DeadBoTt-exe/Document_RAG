"""
Core RAG engine.

Handles query embedding, vector search via Qdrant, prompt construction,
LLM invocation, grounding validation, and confidence scoring.
"""

from typing import Dict, List
import os
import logging
import numpy as np
from dotenv import load_dotenv
import google.genai as genai
from qdrant_client import QdrantClient

from code.confidence import ConfidenceScorer
from code.embeddings import EmbeddingModel
from code.validator import GroundingValidator

load_dotenv()

logger = logging.getLogger(__name__)

COLLECTION_NAME = "aws-org-docs"


class RAGEngine:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment")

        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.5-flash"

        self.embedder = EmbeddingModel()

        self.validator = GroundingValidator()

        self.confidence_scorer = ConfidenceScorer()

        self.qdrant = QdrantClient(
            host="localhost",
            port=6333,
        )

        collections = [
            c.name for c in self.qdrant.get_collections().collections
        ]
        if COLLECTION_NAME not in collections:
            raise RuntimeError(
                f"Qdrant collection '{COLLECTION_NAME}' not found. "
                "Run index_documents.py first."
            )

    def ask(self, question: str, top_k: int = 5) -> Dict:
        query_embedding = self.embedder.embed([question])
        query_embedding = query_embedding / np.linalg.norm(
            query_embedding, axis=1, keepdims=True
        )
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
                "validation": {
                    "is_valid": False,
                    "reason": "No relevant context retrieved.",
                },
                "confidence": 0.0,
            }

        context_chunks: List[str] = []
        sources = set()
        retrieval_scores: List[float] = []

        for r in results:
            payload = r.payload or {}

            text = payload.get("text")
            file = payload.get("file")
            page = payload.get("page")

            if not text or not file or page is None:
                logger.warning(f"Skipping malformed chunk: {payload}")
                continue

            context_chunks.append(text)
            sources.add(f"{file}#page-{page}")
            retrieval_scores.append(r.score)

        if not context_chunks:
            return {
                "answer": "I don't know based on the documentation.",
                "sources": [],
                "validation": {
                    "is_valid": False,
                    "reason": "Retrieved chunks were empty or malformed.",
                },
                "confidence": 0.0,
            }

        context = "\n\n".join(context_chunks)

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

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            answer = response.text.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                "answer": "An error occurred while generating the answer.",
                "sources": sorted(sources),
                "validation": {
                    "is_valid": False,
                    "reason": f"LLM error: {str(e)}",
                },
                "confidence": 0.0,
            }

        try:
            validation = self.validator.validate(
                question=question,
                answer=answer,
                context=context,
            )
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation = {
                "is_valid": False,
                "reason": f"Validation error: {str(e)}",
            }

        confidence = self.confidence_scorer.score(
            retrieval_scores=retrieval_scores,
            num_chunks=len(context_chunks),
            is_valid=validation["is_valid"],
        )

        if not validation["is_valid"]:
            return {
                "answer": "The answer could not be confidently validated against the documentation.",
                "sources": sorted(sources),
                "validation": validation,
                "confidence": confidence,
            }

        return {
            "answer": answer,
            "sources": sorted(sources),
            "validation": validation,
            "confidence": confidence,
        }
