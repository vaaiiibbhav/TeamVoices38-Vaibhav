"""The constrained answer prompt.

Hard rules: use only the numbered CONTEXT blocks, every factual sentence ends
with an [n] marker, insufficient context gets the exact sentinel below, never
invent a page, section, office, deadline, or email.
"""
from __future__ import annotations

from services.api.rag.schemas import Source

INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

SYSTEM_PROMPT = f"""You are CampusFlow, a campus helpdesk assistant. You answer \
questions about university policy using ONLY the numbered CONTEXT blocks \
provided below the question. These rules have no exceptions:

1. Every factual sentence in your answer must end with a citation marker \
matching a CONTEXT block number, e.g. "...within 72 hours [3]." Use the \
number of the block the fact actually came from. The marker MUST use plain \
ASCII square brackets exactly like [3] — never full-width or CJK-style \
brackets such as 【 3 】, and never any other bracket or parenthesis style.
2. Use only information present in the CONTEXT blocks. Do not use outside \
knowledge, even if you believe it to be true or commonly known.
3. Never invent a page number, section, office name, deadline, or email \
address. If a detail is not stated in the CONTEXT, do not state it.
4. If the CONTEXT blocks do not contain enough information to answer the \
question, respond with exactly this and nothing else: {INSUFFICIENT_CONTEXT}
"""


def build_context_blocks(sources: list[Source]) -> str:
    """Numbered context blocks built directly from each Source's precomputed
    citation header and snippet — not a reformatted citation string."""
    return "\n\n".join(
        f"[{i}] {source.header}\n{source.snippet}"
        for i, source in enumerate(sources, start=1)
    )


def build_answer_messages(question: str, sources: list[Source]) -> list[dict]:
    """Chat-completion messages for the constrained answer call."""
    context = build_context_blocks(sources)
    user_content = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
