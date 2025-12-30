from app.rag import RAGEngine

if __name__ == "__main__":
    rag = RAGEngine()
    result = rag.ask("Where is GST calculated?")

    print("\nANSWER:")
    print(result["answer"])

    print("\nSOURCES:")
    for src in result["sources"]:
        print("-", src)
