"""
Content classification.

Two layers:
  1. Cheap, deterministic rules for content_type (image/video/carousel/
     text/link) based on fields the connectors already give us -- no API
     call, no cost, runs on every post.
  2. Optional richer tagging (topics + audience-tone read + sentiment)
     via the Anthropic API, for mentions/captions where you want more
     than a type label. Only runs if ANTHROPIC_API_KEY is set, and is
     called in small batches to keep cost predictable.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

HASHTAG_RE = re.compile(r"#(\w+)")


def classify_content_type(raw_post: Dict[str, Any]) -> str:
    """Deterministic content-type classification from connector output."""
    if raw_post.get("content_type"):
        # Some connectors (e.g. Twitter) already give a best-effort guess
        guess = raw_post["content_type"]
        if guess != "image_or_video":
            return guess

    attachments = raw_post.get("raw", {}).get("attachments") if isinstance(raw_post.get("raw"), dict) else None
    if attachments:
        media_keys = attachments.get("media_keys", [])
        if len(media_keys) > 1:
            return "carousel"
        if media_keys:
            return "image_or_video"

    text = raw_post.get("caption") or raw_post.get("text") or ""
    if re.search(r"https?://", text):
        return "link"
    return "text"


def extract_hashtags(text: str) -> List[str]:
    return [f"#{h}" for h in HASHTAG_RE.findall(text or "")]


def classify_with_claude(text: str) -> Optional[Dict[str, Any]]:
    """
    Use the Anthropic API to extract topics, likely target audience, and
    sentiment from a post/mention's text. Returns None (and logs a
    warning) if no API key is configured, rather than raising -- callers
    should treat this as an enrichment, not a requirement.
    """
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set -- skipping Claude-based content tagging.")
        return None
    if not text or not text.strip():
        return None

    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed -- run `pip install anthropic`.")
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = (
        "Analyze this social media post/mention. Respond with ONLY a JSON object, "
        "no other text, in this exact shape:\n"
        '{"topics": ["..."], "likely_audience": "...", "sentiment": "positive|neutral|negative", '
        '"sentiment_score": -1.0 to 1.0, "tone": "..."}\n\n'
        f"Text: {text[:2000]}"
    )

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:  # noqa: BLE001 -- log and degrade gracefully
        logger.error("Claude content classification failed: %s", e)
        return None
