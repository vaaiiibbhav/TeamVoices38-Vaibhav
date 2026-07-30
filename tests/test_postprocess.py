"""Plain-assert self-check for rag/postprocess.py's enforce_citations —
citation-integrity logic that strips out-of-range markers and renumbers
survivors to match the compacted sources list it returns.
Run with: python tests/test_postprocess.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.rag.postprocess import enforce_citations
from services.api.rag.prompts import INSUFFICIENT_CONTEXT
from services.api.rag.schemas import Source


def make_source(n: int) -> Source:
    return Source(
        doc_id=f"doc{n}", doc_title=f"Doc {n}", page=n, section="s",
        snippet="text", score=1.0, header="h",
    )


sources = [make_source(1), make_source(2), make_source(3), make_source(4), make_source(5)]

# Only source [2] is ever cited -> cited_sources compacts to 1 item, and the
# surviving marker must be renumbered [2] -> [1] to stay a valid index.
answer, cited = enforce_citations("Area is 17,467 sq.mt [2]. It has six floors [2].", sources)
assert answer == "Area is 17,467 sq.mt [1]. It has six floors [1].", answer
assert cited == [sources[1]]

# A sentence mixing a valid marker with an out-of-range one is dropped whole,
# same treatment as a sentence with no marker at all.
answer, cited = enforce_citations("Fact one [1]. Fact two [1][9].", sources)
assert answer == "Fact one [1].", answer
assert cited == [sources[0]]

# A marker beyond len(sources) with nothing else valid in the sentence -> INSUFFICIENT_CONTEXT.
answer, cited = enforce_citations("Made up fact [9].", sources)
assert answer == INSUFFICIENT_CONTEXT
assert cited == []

# Two distinct cited sources renumber by original source order, not mention order.
answer, cited = enforce_citations("First [4]. Second [1].", sources)
assert answer == "First [2]. Second [1].", answer
assert cited == [sources[0], sources[3]]

print("test_postprocess: all assertions passed")
