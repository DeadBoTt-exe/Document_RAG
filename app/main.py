from fastapi import FastAPI
from pydantic import BaseModel
from app.rag import RAGEngine

app = FastAPI(title="Engineering Docs RAG")
rag = RAGEngine()

class Query(BaseModel):
    question: str

@app.post("/ask")
def ask(query: Query):
    return rag.ask(query.question)

@app.get("/health")
def health():
    return {"status": "ok"}
