"""Parse a policy PDF into cited, embedded chunks and index them in Qdrant.

Per-page text -> regex section labels -> 700-token chunks (120 overlap, never
crossing a page boundary) -> citation header prepended before embedding.
"""
from __future__ import annotations

import argparse
import os
import re
import uuid
from pathlib import Path

import fitz
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "services/api/qdrant_data")
COLLECTION = "campus_docs"

CHUNK_TOKENS = 700
OVERLAP_TOKENS = 120

SECTION_RE = re.compile(r"(Chapter\s+\d+\s*[—-]\s*.+)")

_embedder: SentenceTransformer | None = None
_client: QdrantClient | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def get_qdrant_client() -> QdrantClient:
    """Docker Qdrant when QDRANT_URL is set, embedded on-disk mode otherwise."""
    global _client
    if _client is None:
        _client = (
            QdrantClient(url=QDRANT_URL)
            if QDRANT_URL
            else QdrantClient(path=QDRANT_LOCAL_PATH)
        )
    return _client


def ensure_collection(client: QdrantClient, vector_size: int) -> None:
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=qmodels.VectorParams(
                size=vector_size, distance=qmodels.Distance.COSINE
            ),
        )


def _page_texts(pdf_path: Path) -> list[str]:
    with fitz.open(pdf_path) as doc:
        return [page.get_text() for page in doc]


def _section_at(text: str, offset: int) -> str:
    section = "General"
    for match in SECTION_RE.finditer(text[:offset]):
        section = match.group(1).strip()
    return section


def _chunk_page(text: str, tokenizer) -> list[tuple[str, str]]:
    """Return (section, chunk_text) pairs for one page's text."""
    offsets = tokenizer(
        text, return_offsets_mapping=True, add_special_tokens=False
    )["offset_mapping"]
    if not offsets:
        return []

    chunks = []
    start = 0
    n = len(offsets)
    while start < n:
        end = min(start + CHUNK_TOKENS, n)
        char_start = offsets[start][0]
        char_end = offsets[end - 1][1]
        chunk_text = text[char_start:char_end].strip()
        if chunk_text:
            chunks.append((_section_at(text, char_end), chunk_text))
        if end == n:
            break
        start = end - OVERLAP_TOKENS
    return chunks


def ingest_pdf(pdf_path: str, title: str, doc_type: str) -> int:
    """Parse, chunk, embed, and index one PDF. Returns chunk count."""
    path = Path(pdf_path)
    doc_id = path.stem

    embedder = get_embedder()
    client = get_qdrant_client()
    ensure_collection(client, embedder.get_embedding_dimension())

    points = []
    for page_num, page_text in enumerate(_page_texts(path), start=1):
        for chunk_index, (section, chunk_text) in enumerate(
            _chunk_page(page_text, embedder.tokenizer)
        ):
            header = f"[{title} | p.{page_num} | {section}]"
            vector = embedder.encode(
                f"{header}\n{chunk_text}", normalize_embeddings=True
            ).tolist()
            point_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}:{page_num}:{chunk_index}")
            )
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "doc_id": doc_id,
                        "title": title,
                        "doc_type": doc_type,
                        "page": page_num,
                        "section": section,
                        "text": chunk_text,
                        "header": header,
                        "source_path": str(path),
                    },
                )
            )

    if points:
        client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest a PDF into the CampusFlow vector store."
    )
    parser.add_argument("pdf_path")
    parser.add_argument("--title", required=True)
    parser.add_argument("--doc-type", required=True)
    args = parser.parse_args()

    count = ingest_pdf(args.pdf_path, title=args.title, doc_type=args.doc_type)
    print(f"Indexed {count} chunks from {args.pdf_path}")
