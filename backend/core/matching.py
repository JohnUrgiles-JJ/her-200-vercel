"""AI mentor matching (Phase 3).

    match_mentors(question_text, k=3) -> [{"mentor_id": <user id>, "reason": "..."}, ...]

Results are ordered best first and have length min(k, number of active mentors).

Provider is chosen per call from the LLM_PROVIDER env var:
    anthropic  -> anthropic SDK, model ANTHROPIC_MODEL (default claude-haiku-5-5)
    openai     -> openai SDK,    model OPENAI_MODEL    (default gpt-4o-mini)
    none       -> keyword fallback only
A missing API key also means "keyword fallback only". Any failure in the LLM path (network, auth,
timeout, refusal, unparseable output) is logged as a warning and the keyword fallback is returned,
so asking a question never fails because of the LLM.
"""

import json
import logging
import os
import re

from .models import MentorProfile

logger = logging.getLogger(__name__)

# Per-request timeout (max_retries=0, so this is the worst case). Measured against a server that never
# answers: 10 s, then the keyword fallback. A normal Haiku/gpt-4o-mini match takes a few seconds.
LLM_TIMEOUT_SECONDS = 10.0
ANTHROPIC_MAX_TOKENS = 500
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-5-5"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
BIO_CHARS = 300
REASON_MAX_CHARS = 200  # QuestionMatch.reason max_length


# --- Public API --------------------------------------------------------------


def match_mentors(question_text: str, k: int = 3) -> list[dict]:
    mentors = list(
        MentorProfile.objects.filter(is_active=True, user__is_active=True)
        .select_related("user", "user__profile")
        .order_by("user_id")
    )
    if not mentors or k <= 0:
        return []
    k = min(k, len(mentors))

    provider, api_key, model = _provider_config()
    if provider == "none" or not api_key:
        return keyword_fallback(question_text, mentors, k)

    try:
        prompt = build_prompt(question_text, mentors, k)
        if provider == "anthropic":
            raw = _call_anthropic(prompt, api_key, model)
        else:
            raw = _call_openai(prompt, api_key, model)
        results = parse_llm_response(raw, {m.user_id for m in mentors})
    except Exception as exc:  # never let the LLM break asking a question
        logger.warning("LLM matching failed (%s, %s): %r. Using keyword fallback.", provider, model, exc)
        return keyword_fallback(question_text, mentors, k)

    results = results[:k]
    if len(results) < k:
        logger.warning(
            "LLM returned %d valid matches out of %d; topping up from keyword fallback.", len(results), k
        )
        chosen = {r["mentor_id"] for r in results}
        rest = [m for m in mentors if m.user_id not in chosen]
        results += keyword_fallback(question_text, rest, k - len(results))
    return results


# --- Provider config ---------------------------------------------------------


def _env(name, default=""):
    # Defensive: strip an inline "# comment" in case a .env loader keeps it.
    return os.environ.get(name, default).split("#", 1)[0].strip()


def _provider_config():
    provider = _env("LLM_PROVIDER", "none").lower() or "none"
    if provider == "anthropic":
        return provider, _env("ANTHROPIC_API_KEY"), _env("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    if provider == "openai":
        return provider, _env("OPENAI_API_KEY"), _env("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    if provider != "none":
        logger.warning("Unknown LLM_PROVIDER %r; using keyword fallback.", provider)
    return "none", "", ""


FALLBACK_NOTICE = "Using keyword fallback for matching."


def log_startup_status():
    """One clear line at server start saying how matching will work. Called from connecther/asgi.py.

    Returns the message (for tests). A warning when matching will use the keyword fallback, info otherwise.
    """
    raw = _env("LLM_PROVIDER", "none").lower() or "none"
    if raw == "none":
        message = f"LLM_PROVIDER=none. {FALLBACK_NOTICE}"
    elif raw not in ("anthropic", "openai"):
        message = f"Unknown LLM_PROVIDER={raw!r} (use anthropic, openai or none). {FALLBACK_NOTICE}"
    else:
        _, api_key, model = _provider_config()
        if api_key:
            message = (
                f"Matching uses {raw} ({model}), {LLM_TIMEOUT_SECONDS:g}s timeout; "
                "keyword fallback on any LLM error."
            )
            logger.info(message)
            # Import the SDK now (it takes a few seconds) so the first question of the demo doesn't pay it.
            try:
                __import__(raw)
            except Exception:
                logger.warning("Could not import the %s SDK; every match will use the keyword fallback.", raw)
            return message
        message = f"No LLM key set: LLM_PROVIDER={raw} but {raw.upper()}_API_KEY is empty. {FALLBACK_NOTICE}"
    logger.warning(message)
    return message


# --- Prompt ------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You match a student's question to the mentors on ConnectHER, a mentorship platform for women "
    "and girls breaking into STEM. Pick the mentors whose real experience best equips them to answer "
    "this specific question. Give extra weight to a mentor's \"open_to\" topics and to lived "
    "experience in their bio (for example career switching, being first-gen, immigrating, returning "
    "after a break, or getting in without a degree) when it mirrors the student's situation. Job "
    "title alone is not enough: prefer the mentor who has actually lived what the student is asking "
    "about.\n\n"
    "Respond with ONLY a JSON array, no markdown, no code fences, no commentary."
)


def _clean(value, limit=None):
    text = " ".join(str(value or "").replace("|", "/").split())
    if limit and len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text


def _mentor_name(mentor):
    profile = getattr(mentor.user, "profile", None)
    return profile.full_name if profile else (mentor.user.get_full_name() or mentor.user.username)


def build_prompt(question_text: str, mentors, k: int) -> str:
    lines = [
        " | ".join(
            [
                str(m.user_id),
                _clean(_mentor_name(m)),
                _clean(m.headline),
                _clean(m.company),
                _clean(m.fields),
                _clean(m.open_to),
                _clean(m.bio, BIO_CHARS),
            ]
        )
        for m in mentors
    ]
    return (
        f"Student's question:\n\"\"\"\n{question_text.strip()}\n\"\"\"\n\n"
        "Mentors (id | name | headline | company | fields | open_to | bio):\n"
        + "\n".join(lines)
        + "\n\n"
        f"Return ONLY a JSON array of exactly {k} objects, best match first, each shaped "
        '{"mentor_id": <int id from the list>, "reason": "<string>"}. Use each mentor at most once. '
        "Each reason must be under 15 words, speak to the student in the second or third person, and "
        "name the specific experience that makes this mentor a fit (for example: "
        "\"Switched into UX from teaching, just like you're hoping to\"). No markdown."
    )


# --- Provider calls ----------------------------------------------------------


def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key, timeout=LLM_TIMEOUT_SECONDS, max_retries=0)
    kwargs = {}
    if model.startswith("claude-haiku-5"):
        # Haiku 5.5 thinks by default; with only 500 output tokens we want all of them for the answer.
        kwargs["thinking"] = {"type": "disabled"}
    response = client.messages.create(
        model=model,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("model refused the matching request")
    return "".join(block.text for block in response.content if block.type == "text")


def _call_openai(prompt: str, api_key: str, model: str) -> str:
    import openai

    client = openai.OpenAI(api_key=api_key, timeout=LLM_TIMEOUT_SECONDS, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


# --- Parsing -----------------------------------------------------------------


def parse_llm_response(raw: str, valid_ids: set) -> list[dict]:
    """Extract [{"mentor_id", "reason"}] from model text. Raises ValueError if there's no JSON array.

    Items that aren't objects, or whose mentor_id is unknown or repeated, are dropped. Reasons are
    whitespace-normalized and capped at REASON_MAX_CHARS; a blank reason gets a generic line.
    """
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON array in LLM output: {raw[:200]!r}")
    data = json.loads(raw[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("LLM output is not a JSON array")

    results, seen = [], set()
    for item in data:
        if not isinstance(item, dict):
            continue
        mentor_id = _as_int(item.get("mentor_id"))
        if mentor_id is None or mentor_id not in valid_ids or mentor_id in seen:
            continue
        reason = " ".join(str(item.get("reason") or "").split()).strip("\"' ")
        if len(reason) > REASON_MAX_CHARS:
            reason = reason[: REASON_MAX_CHARS - 3].rstrip() + "..."
        seen.add(mentor_id)
        results.append({"mentor_id": mentor_id, "reason": reason or "Relevant experience for your question"})
    return results


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


# --- Keyword fallback --------------------------------------------------------

STOPWORDS = {
    "a", "about", "after", "all", "am", "an", "and", "any", "are", "as", "at", "be", "been", "but",
    "by", "can", "could", "did", "do", "does", "for", "from", "get", "getting", "had", "has", "have",
    "how", "i", "if", "im", "in", "into", "is", "it", "its", "just", "like", "me", "my", "no", "not",
    "of", "on", "or", "should", "so", "some", "that", "the", "their", "them", "then", "there", "they",
    "this", "to", "too", "up", "was", "we", "what", "when", "where", "which", "who", "why", "will",
    "with", "would", "you", "your", "really", "want", "know", "any", "best", "good", "way", "ways",
    "start", "need", "much", "more", "very", "one", "also", "other", "than", "these", "those",
    "experience", "experienced",  # appears in nearly every bio and open_to, so it carries no signal
}
FIELD_WEIGHT, OPEN_TO_WEIGHT, HEADLINE_WEIGHT, BIO_WEIGHT = 2.0, 2.0, 1.0, 0.5

_WORD_RE = re.compile(r"[a-z0-9+#]+")


def _normalize(word: str) -> str:
    # Tiny stemmer so "certifications"/"certification" and "internships"/"internship" match.
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text: str) -> set:
    words = _WORD_RE.findall((text or "").lower().replace("'", ""))
    return {_normalize(w) for w in words if w not in STOPWORDS and len(w) > 1}


def _split_list(value: str) -> list:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def keyword_fallback(question_text: str, mentors, k: int) -> list[dict]:
    """Score mentors by word overlap with the question and return the top k as match dicts."""
    q_tokens = tokenize(question_text)
    scored = []
    for m in mentors:
        sources = (
            (tokenize(m.fields), FIELD_WEIGHT),
            (tokenize(m.open_to), OPEN_TO_WEIGHT),
            (tokenize(m.headline), HEADLINE_WEIGHT),
            (tokenize(m.bio), BIO_WEIGHT),
        )
        score = sum(weight for tokens, weight in sources for t in q_tokens if t in tokens)
        scored.append((score, m.experience_years or 0, m))

    # Highest score first, then more experience; stable for full ties (input order = user id).
    scored.sort(key=lambda s: (-s[0], -s[1]))
    return [{"mentor_id": m.user_id, "reason": _fallback_reason(m, q_tokens)} for _, _, m in scored[: max(k, 0)]]


def _fallback_reason(mentor, q_tokens: set) -> str:
    fields = _split_list(mentor.fields)
    if not fields:
        return f"Experience as {mentor.headline}"[:REASON_MAX_CHARS] if mentor.headline else "Relevant experience"
    # The field or open_to topic sharing the most words with the question (fields win ties), so a
    # mentor picked for "imposter syndrome" says so rather than naming an unrelated field.
    # No overlap at all: the first field.
    candidates = fields + _split_list(mentor.open_to)
    overlaps = [len(tokenize(c) & q_tokens) for c in candidates]
    best = max(range(len(candidates)), key=lambda i: (overlaps[i], -i))
    matching = candidates[best] if overlaps[best] else fields[0]
    return f"Experience in {matching}"[:REASON_MAX_CHARS]
