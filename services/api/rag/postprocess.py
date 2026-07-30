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
        valid_markers = [
            n
            for n in (int(m) for m in _MARKER_RE.findall(sentence))
            if 1 <= n <= len(sources)
        ]
        if not valid_markers:
            continue
        kept_sentences.append(sentence)
        for n in valid_markers:
            if n not in cited_indices:
                cited_indices.append(n)

    if not kept_sentences:
        return INSUFFICIENT_CONTEXT, []

    final_answer = " ".join(kept_sentences)
    cited_sources = [sources[n - 1] for n in sorted(cited_indices)]
    return final_answer, cited_sources
