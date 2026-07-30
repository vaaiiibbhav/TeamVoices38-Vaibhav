"""Dense retrieval over the indexed policy chunks."""
from __future__ import annotations

from qdrant_client.http import models as qmodels

from services.api.rag.ingest import COLLECTION, get_embedder, get_qdrant_client
from services.api.rag.schemas import Source


def search(query: str, doc_types: list[str] | None, k: int) -> list[Source]:
    """Dense-only search. doc_types=None means unfiltered."""
    embedder = get_embedder()
    client = get_qdrant_client()
    vector = embedder.encode(query, normalize_embeddings=True).tolist()

    query_filter = None
    if doc_types:
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="doc_type", match=qmodels.MatchAny(any=doc_types)
                )
            ]
        )

    hits = client.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=query_filter,
        limit=k,
        with_payload=True,
    ).points

    return [
        Source(
            doc_id=hit.payload["doc_id"],
            doc_title=hit.payload["title"],
            page=hit.payload["page"],
            section=hit.payload["section"],
            snippet=hit.payload["text"],
            score=hit.score,
            header=hit.payload["header"],
        )
        for hit in hits
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Query the CampusFlow vector store.")
    parser.add_argument("query")
    parser.add_argument("--doc-types", nargs="*", default=None)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    for source in search(args.query, doc_types=args.doc_types, k=args.k):
        print(f"[{source.score:.4f}] {source.header}\n  {source.snippet[:150]}")
