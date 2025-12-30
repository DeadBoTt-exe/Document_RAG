from pathlib import Path
from typing import List, Dict
from .chunker import chunk_markdown

DOCS_DIR = Path("docs")


def load_markdown_files() -> List[Dict]:
    all_chunks: List[Dict] = []

    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"{DOCS_DIR} directory not found")

    for md_file in DOCS_DIR.glob("*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_markdown(content, md_file.name)
        print(f"{md_file.name} -> {len(chunks)} chunks")
        all_chunks.extend(chunks)

    return all_chunks


if __name__ == "__main__":
    chunks = load_markdown_files()
    print(f"\nLoaded {len(chunks)} chunks\n")

