"""Conservative, model-independent admission checks for English policy requests.

Retrieval always returns nearest neighbours in dense mode; their presence (or RRF
rank) is not evidence that a question is relevant. Require meaningful lexical overlap
with an actual search hit, excluding generic policy and conversational vocabulary.
This is a heuristic, not a semantic classifier or a complete prompt-injection defence.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.workflow.retrieval import Evidence

VERSION = "policy-input-v1"
SCOPE_MESSAGE = (
    "I couldn't connect this request to the available policies, so I haven't generated "
    "an answer or assessment. Ask a policy question or start a new case about a business activity, "
    "including the data, people, systems or approvals involved."
)
INSTRUCTION_MESSAGE = (
    "I can check business activities against policies, but I won't follow requests to "
    "override my instructions or force a result. Describe the activity you want checked."
)

# Common words must not make weather, greetings or abuse look like policy evidence.
STOP_WORDS = set(
    """
a an the and or but if then than as at by for from in into of on to with without
i me my mine we us our ours you your yours he she it its they them their this that
these those is am are was were be been being do does did have has had can could
may might must shall should will would not no yes so very just really also all any
some each other such what which who whom whose when where why how about please
tell say give show explain help want need know ask question answer describe check
policy policies compliance compliant rule rules requirement requirements clause
clauses kestrel mutual business activity scenario today tomorrow yesterday now
new use used using make made get got go going come bring after before during
there here only more most much many like time day days week month year work
office lunch friday fridays hello hi thanks thank stuff thing things don t s
""".split()  # noqa: SIM905 - keep the vocabulary readable
)

# Normalize common policy inflections without a model or an extra runtime download.
ALIASES = {
    "approval": "approve",
    "approvals": "approve",
    "approved": "approve",
    "approves": "approve",
    "approving": "approve",
    "sharing": "share",
    "shared": "share",
    "shares": "share",
    "retention": "retain",
    "retained": "retain",
    "retaining": "retain",
    "deletion": "delete",
    "deleted": "delete",
    "deleting": "delete",
    "working": "work",
}

REDIRECTION = re.compile(
    r"\b(?:ignore|forget|disregard|override)\b.{0,60}\b(?:instructions?|prompts?|rules|policies)\b"
    r"|\b(?:reveal|print|show|repeat)\b.{0,40}\b(?:system prompt|api key|secret key)\b"
    r"|\b(?:mark|declare|label|output|say)\b.{0,35}\bcompliant\b.{0,40}"
    r"\b(?:regardless|anyway|no matter)\b"
    r"|\b(?:mark|declare|label)\s+(?:everything|all|this)\s+(?:as\s+)?compliant\b",
    re.IGNORECASE,
)
ENTERTAINMENT = re.compile(
    r"\b(?:tell|write|generate|sing)\b.{0,30}\b(?:joke|poem|song|story)\b",
    re.IGNORECASE,
)
TRIVIA = re.compile(
    r"\bwhat(?:'s| is)\s+(?:the\s+)?weather\b"
    r"|\b(?:give|show|tell)\b.{0,25}\bweather forecast\b"
    r"|\bwhat(?:'s| is)\s+the\s+capital\s+of\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Refusal:
    code: str
    message: str


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z]{2,}", _normalize(text))
    return {
        ALIASES.get(word, word[:-1] if word.endswith("s") and not word.endswith("ss") else word)
        for word in words
        if word not in STOP_WORDS
    } - STOP_WORDS


def screen(text: str, *, allow_short_answer: bool = False) -> Refusal | None:
    """Reject obvious redirects and empty/noise input before retrieval or generation."""
    normalized = _normalize(text)
    if REDIRECTION.search(normalized):
        return Refusal("request_redirected", INSTRUCTION_MESSAGE)
    if ENTERTAINMENT.search(normalized) or TRIVIA.search(normalized):
        return Refusal("request_out_of_scope", SCOPE_MESSAGE)
    if not allow_short_answer and not _terms(normalized):
        return Refusal("request_out_of_scope", SCOPE_MESSAGE)
    return None


def check_evidence(text: str, evidence: Evidence) -> Refusal | None:
    """Admit only a meaningful match in one search hit, not aggregated incidental words.

    Two matching content terms and 25% query coverage are the normal minimum;
    two topical heading matches also admit detailed narratives with incidental facts.
    A one-term question needs an exact topical heading/title match. Definitions and
    linked exceptions added as context cannot independently establish relevance.
    Negative facts are deliberately not a rejection signal.
    """
    if refusal := screen(text):
        return refusal
    query = _terms(text)
    for clause in evidence.clauses:
        if clause.reason != "search":
            continue
        topic = _terms(f"{clause.policy_title} {clause.heading}")
        overlap = query & (topic | _terms(clause.text))
        if len(overlap) >= 2 and (len(overlap) / len(query) >= 0.25 or len(query & topic) >= 2):
            return None
        if len(query) == 1 and query & topic:
            return None
    return Refusal("request_out_of_scope", SCOPE_MESSAGE)
