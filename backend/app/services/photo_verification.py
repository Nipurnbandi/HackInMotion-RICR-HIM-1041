"""AI photo verification via the Claude API.

Report photos are checked against the reported category, and resolution
photos against "does this show the issue fixed?". Runs as a background
task after upload; a missing API key or any API failure degrades to an
UNVERIFIED verdict rather than blocking the report flow.
"""
from __future__ import annotations

import base64
import json

import anthropic

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.issue_types import CATEGORY_LABELS
from app.models import Issue

VERDICT_MATCH = "MATCH"
VERDICT_MISMATCH = "MISMATCH"
VERDICT_UNVERIFIED = "UNVERIFIED"

_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "match": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["match", "reason"],
    "additionalProperties": False,
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _report_prompt(issue: Issue) -> str:
    label = CATEGORY_LABELS[issue.category]
    return (
        f"A citizen reported a civic issue categorised as: {label}.\n"
        f'Their description: "{issue.description[:500]}"\n\n'
        f"Does this photo plausibly show that type of issue? These are casual "
        f"phone photos taken on the street, so allow for poor framing and "
        f"lighting — judge only whether the subject matter matches the "
        f"category. Answer with match=true/false and a one-sentence reason "
        f"written for a city administrator."
    )


def _resolution_prompt(issue: Issue) -> str:
    label = CATEGORY_LABELS[issue.category]
    return (
        f"A city crew claims to have fixed a reported civic issue.\n"
        f"Issue category: {label}.\n"
        f'Original report: "{issue.description[:500]}"\n\n'
        f"Does this photo plausibly show that issue repaired or resolved "
        f"(e.g. a filled pothole, a working light, a cleared bin)? Answer "
        f"with match=true/false and a one-sentence reason written for a "
        f"city administrator."
    )


def classify_photo(*, content: bytes, media_type: str, prompt: str) -> dict:
    """One vision call → {"verdict": ..., "note": ...}. Never raises."""
    if not settings.anthropic_api_key:
        return {
            "verdict": VERDICT_UNVERIFIED,
            "note": "AI verification is not configured (no ANTHROPIC_API_KEY).",
        }

    try:
        response = _get_client().messages.create(
            model=settings.photo_verification_model,
            max_tokens=2048,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": _VERDICT_SCHEMA},
            },
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.standard_b64encode(content).decode(),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        if response.stop_reason == "refusal":
            return {
                "verdict": VERDICT_UNVERIFIED,
                "note": "AI verification declined to assess this photo.",
            }
        text = next(
            block.text for block in response.content if block.type == "text"
        )
        data = json.loads(text)
        return {
            "verdict": VERDICT_MATCH if data["match"] else VERDICT_MISMATCH,
            "note": str(data.get("reason", ""))[:500],
        }
    except Exception:
        return {
            "verdict": VERDICT_UNVERIFIED,
            "note": "AI verification was unavailable — checked manually instead.",
        }


def _store(issue_id: int, *, verdict_field: str, note_field: str, result: dict) -> None:
    db = SessionLocal()
    try:
        issue = db.get(Issue, issue_id)
        if issue is not None:
            setattr(issue, verdict_field, result["verdict"])
            setattr(issue, note_field, result["note"])
            db.commit()
    finally:
        db.close()


def verify_issue_photo(issue_id: int, content: bytes, media_type: str) -> None:
    """Background task: verify a report photo matches its category."""
    db = SessionLocal()
    try:
        issue = db.get(Issue, issue_id)
        if issue is None:
            return
        prompt = _report_prompt(issue)
    finally:
        db.close()

    result = classify_photo(content=content, media_type=media_type, prompt=prompt)
    _store(
        issue_id,
        verdict_field="photo_verdict",
        note_field="photo_verdict_note",
        result=result,
    )


def verify_resolution_photo(issue_id: int, content: bytes, media_type: str) -> None:
    """Background task: verify a proof photo shows the issue fixed."""
    db = SessionLocal()
    try:
        issue = db.get(Issue, issue_id)
        if issue is None:
            return
        prompt = _resolution_prompt(issue)
    finally:
        db.close()

    result = classify_photo(content=content, media_type=media_type, prompt=prompt)
    _store(
        issue_id,
        verdict_field="resolution_photo_verdict",
        note_field="resolution_photo_verdict_note",
        result=result,
    )
