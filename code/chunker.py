from typing import List, Dict
import uuid


def chunk_text(
    text: str,
    *,
    source_file: str,
    page: int,
    service: str,
    max_chars: int = 800,  # Industry standard: 512-1000 tokens
    overlap: int = 100,    # ~12.5% overlap for context continuity

) -> List[Dict]:
    chunks: List[Dict] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end].strip()

        if len(chunk) < 100:
            break

        chunks.append({
            "id": str(uuid.uuid4()),
            "text": chunk,
            "metadata": {
                "file": source_file,
                "page": page,
                "service": service,
            }
        })

        start = max(end - overlap, start + 1)  # Ensure forward progress to avoid infinite loop

    return chunks
