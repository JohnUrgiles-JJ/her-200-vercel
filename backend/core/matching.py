"""Pick the top mentors for a question: one Claude call, keyword fallback."""
import logging
import re

import anthropic
from pydantic import BaseModel

from .models import MentorProfile

log = logging.getLogger(__name__)
TOP_N = 3


class Pick(BaseModel):
    mentor_id: int
    reason: str


class Picks(BaseModel):
    matches: list[Pick]


def _describe(mp: MentorProfile) -> str:
    return (
        f"id={mp.user_id} | {mp.user.profile.full_name} | {mp.headline} at {mp.company} | "
        f"{mp.experience_years} yrs | fields: {', '.join(mp.fields)} | open to: {', '.join(mp.open_to)} | bio: {mp.bio}"
    )


def _llm_match(text: str, mentors: list[MentorProfile]) -> list[dict]:
    client = anthropic.Anthropic()
    roster = "\n".join(_describe(m) for m in mentors)
    response = client.messages.parse(
        model="claude-opus-5-5",
        max_tokens=2000,
        output_config={"effort": "low"},
        system=(
            "You match a student's career or STEM question to the mentors best placed to answer it. "
            f"Choose up to {TOP_N} mentors from the roster, best first, using only the given ids. "
            "For each, write one short sentence (under 20 words) telling the student why this mentor fits."
        ),
        messages=[{"role": "user", "content": f"Mentors:\n{roster}\n\nQuestion: {text}"}],
        output_format=Picks,
    )
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"No usable match output (stop_reason={response.stop_reason})")
    valid = {m.user_id for m in mentors}
    picks, seen = [], set()
    for p in response.parsed_output.matches:
        if p.mentor_id in valid and p.mentor_id not in seen:
            seen.add(p.mentor_id)
            picks.append({"mentor_id": p.mentor_id, "reason": p.reason})
    if not picks:
        raise RuntimeError("Model returned no valid mentor ids")
    return picks[:TOP_N]


def _keyword_match(text: str, mentors: list[MentorProfile]) -> list[dict]:
    words = set(re.findall(r"[a-z]{3,}", text.lower()))
    scored = []
    for m in mentors:
        terms = [*m.fields, *m.open_to, m.headline]
        hits = [t for t in terms if words & set(re.findall(r"[a-z]{3,}", t.lower()))]
        scored.append((len(hits), m.experience_years, m, hits))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [
        {
            "mentor_id": m.user_id,
            "reason": f"Experienced in {', '.join(hits[:2])}." if hits else f"{m.headline} with {m.experience_years} years of experience.",
        }
        for _, _, m, hits in scored[:TOP_N]
    ]


def match_mentors(text: str) -> list[dict]:
    mentors = list(MentorProfile.objects.select_related("user__profile"))
    if not mentors:
        return []
    try:
        return _llm_match(text, mentors)
    except Exception:
        log.exception("LLM matching failed; using keyword fallback")
        return _keyword_match(text, mentors)
