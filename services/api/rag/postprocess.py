"""Strip any answer sentence lacking a valid [n] citation marker.

If nothing survives the strip, the answer is treated as INSUFFICIENT_CONTEXT
too — an uncited answer is not shown to the student, ever.
"""
from __future__ import annotations

import re

from services.api.rag.prompts import INSUFFICIENT_CONTEXT
from services.api.rag.schemas import Source

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])")
_MARKER_RE = re.compile(r"\[(\d+)\]")


def enforce_citations(
    raw_answer: str, sources: list[Source]
) -> tuple[str, list[Source]]:
    """Returns (final_answer, cited_sources). final_answer is the
    INSUFFICIENT_CONTEXT sentinel, with cited_sources=[], whenever the model
    said so directly or every sentence got stripped for lacking a citation."""
    raw_answer = raw_answer.strip()
    if raw_answer == INSUFFICIENT_CONTEXT or not raw_answer:
        return INSUFFICIENT_CONTEXT, []

    kept_sentences = []
    cited_indices: list[int] = []
    for sentence in _SENTENCE_SPLIT_RE.split(raw_answer):
        sentence = sentence.strip()
        if not sentence:
            continue
        markers = [int(m) for m in _MARKER_RE.findall(sentence)]
        if not markers:
            continue
        # A sentence with even one out-of-range marker is treated exactly
        # like a sentence with no marker at all — not meaningfully different.
        if any(not (1 <= n <= len(sources)) for n in markers):
            continue
        kept_sentences.append(sentence)
        for n in markers:
            if n not in cited_indices:
                cited_indices.append(n)

    if not kept_sentences:
        return INSUFFICIENT_CONTEXT, []

    cited_indices.sort()
    cited_sources = [sources[n - 1] for n in cited_indices]
    # cited_sources is a compacted subset of the original sources, so a
    # surviving "[n]" must be renumbered to n's new (1-based) position here —
    # otherwise the marker still points at its old index into a shorter list.
    renumber = {old: new for new, old in enumerate(cited_indices, start=1)}
    final_answer = _MARKER_RE.sub(
        lambda m: f"[{renumber[int(m.group(1))]}]", " ".join(kept_sentences)
    )
    return final_answer, cited_sources
