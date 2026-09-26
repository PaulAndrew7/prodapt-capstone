"""Clause-aligned chunks (plan §6.1 step 8).

A chunk never crosses a clause boundary. Short clauses stay whole; long ones split on
sentence boundaries into windows of about 350 tokens with up to 40 tokens of overlap.
Token counts are a conservative estimate for the BGE WordPiece tokenizer (about 1.35
tokens per English word); the embedder still refuses input over its 512-token limit.
"""

import hashlib
import math
import re
from dataclasses import dataclass

CHUNKER_VERSION = "chunker-v1"
TARGET_TOKENS = 350
OVERLAP_TOKENS = 40
SENTENCE_RE = re.compile(r"(?<=[.;:])\s+(?=[A-Z(“\"])")


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return max(1, math.ceil(max(words * 1.35, len(text) / 4)))


@dataclass
class ChunkDraft:
    ordinal: int
    prefix: str
    text: str
    token_count: int
    content_hash: str


def chunk_prefix(policy_title: str, section_path: list[str], headings: list[str]) -> str:
    parts = [f"{num} {title}" for num, title in zip(section_path, headings, strict=True)]
    return " > ".join([policy_title, *parts])


def chunk_clause(prefix: str, text: str) -> list[ChunkDraft]:
    budget = TARGET_TOKENS - estimate_tokens(prefix)
    windows: list[str] = []
    if estimate_tokens(text) <= budget:
        windows.append(text)
    else:
        sentences = SENTENCE_RE.split(text)
        current: list[str] = []
        for sentence in sentences:
            candidate = " ".join([*current, sentence])
            if current and estimate_tokens(candidate) > budget:
                windows.append(" ".join(current))
                overlap: list[str] = []
                for prev in reversed(current):  # carry trailing sentences as overlap
                    if estimate_tokens(" ".join([prev, *overlap])) > OVERLAP_TOKENS:
                        break
                    overlap.insert(0, prev)
                current = [*overlap, sentence]
            else:
                current.append(sentence)
        if current:
            windows.append(" ".join(current))
    drafts = []
    for i, window in enumerate(windows):
        digest = hashlib.sha256(f"{prefix}\n{window}".encode()).hexdigest()
        drafts.append(ChunkDraft(i, prefix, window, estimate_tokens(f"{prefix}\n{window}"), digest))
    return drafts
