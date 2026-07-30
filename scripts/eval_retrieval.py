"""recall@5 and citation accuracy against data/golden_questions.yaml.

Run standalone: `venv\\Scripts\\python.exe scripts\\eval_retrieval.py` from
the repo root. Needs exclusive access to the embedded on-disk Qdrant store
(services/api/qdrant_data/) — stop the dev uvicorn server first, it holds
the same single-writer file lock.

recall@5: does the expected doc/page appear anywhere in the raw top-5
retrieved chunks (services.api.rag.search.search(), independent of the LLM
answer step).

citation accuracy: does at least one [n] marker in the final rendered
answer resolve (in-bounds) to a returned source matching the expected
doc/page. Markers that are out of bounds for the returned source list are
reported, not silently skipped — that's a real citation-integrity failure,
not a scoring edge case.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from services.api.graph.build import app as agent_graph  # noqa: E402
from services.api.graph.build import initial_state  # noqa: E402
from services.api.rag.schemas import Source  # noqa: E402
from services.api.rag.search import search  # noqa: E402

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "data" / "golden_questions.yaml"
_MARKER_RE = re.compile(r"\[(\d+)\]")


def recall_at_5(q: dict, k: int = 5) -> bool | None:
    if not q.get("expect_doc"):
        return None
    sources = search(q["q"], None, k)
    return any(s.doc_id == q["expect_doc"] and s.page == q["expect_page"] for s in sources)


def citation_accuracy(q: dict, answer: str | None, sources: list[Source]) -> bool | None:
    if not q.get("expect_doc") or not answer:
        return None
    markers = [int(m) for m in _MARKER_RE.findall(answer)]
    if not markers:
        return False
    hit = False
    for n in markers:
        if not (1 <= n <= len(sources)):
            print(f"    !! marker [{n}] out of range for {len(sources)} returned sources")
            continue
        s = sources[n - 1]
        if s.doc_id == q["expect_doc"] and s.page == q["expect_page"]:
            hit = True
    return hit


async def main() -> None:
    questions = yaml.safe_load(GOLDEN_PATH.read_text())["questions"]

    recall_hits = recall_total = 0
    citation_hits = citation_total = 0
    band_hits = band_total = 0

    for q in questions:
        if q.get("skip"):
            print(f"SKIP  {q['q'][:60]!r}\n      reason: {q['skip']}")
            continue

        recall = recall_at_5(q)

        state = initial_state(q["q"], trace_id="eval")
        result = await agent_graph.ainvoke(state)

        citation = citation_accuracy(q, result["answer"], result["sources"])

        band_total += 1
        band_ok = result["route"] == q["expect_band"]
        band_hits += int(band_ok)
        if recall is not None:
            recall_total += 1
            recall_hits += int(recall)
        if citation is not None:
            citation_total += 1
            citation_hits += int(citation)

        print(
            f"{'OK ' if band_ok else 'ERR'}  intent={result['intent']!s:<20} "
            f"route={result['route']!s:<8} (want {q['expect_band']:<8}) "
            f"recall={recall} citation={citation}  {q['q'][:55]!r}"
        )

    print()
    print(f"recall@5:          {recall_hits}/{recall_total}" if recall_total else "recall@5:          n/a (no scoreable questions)")
    print(f"citation accuracy: {citation_hits}/{citation_total}" if citation_total else "citation accuracy: n/a")
    print(f"band match:        {band_hits}/{band_total}")


if __name__ == "__main__":
    asyncio.run(main())
