"""Claude-based curation for creative-ai-feed posts."""

import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_BATCH_SIZE = 10

_SYSTEM_PROMPT = """You are a curator for a feed targeting advanced users of creative AI tools (Midjourney, Stable Diffusion, Flux, Kling, Seedance, Gemini, ComfyUI, etc.) and vibe coders who build creative tools.

Your job: evaluate Reddit posts and decide which deserve to be highlighted.

KEEP posts that:
- Share innovative techniques, workflows, or discoveries
- Demonstrate non-obvious uses of AI tools for creative work
- Contain valuable insights from the comments
- Reveal advanced patterns, prompts, or configurations

DISCARD posts that:
- Are just news announcements with no practical insight
- Are beginner questions or basic tutorials
- Are purely opinion/drama without technical substance
- Have generic content that doesn't teach anything specific

Return a JSON array where each element corresponds to the input post at the same index."""


def _truncate(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


def _build_user_message(batch: list[dict]) -> str:
    items = []
    for idx, post in enumerate(batch):
        comments_preview = [
            {
                "author": c.get("author"),
                "score": c.get("score"),
                "body": _truncate(c.get("body"), 200),
            }
            for c in (post.get("top_comments") or [])[:3]
        ]
        items.append(
            {
                "id": idx,
                "title": post.get("title", ""),
                "subreddit": post.get("subreddit", ""),
                "score": post.get("score", 0),
                "body_md": _truncate(post.get("body_md"), 500),
                "top_comments": comments_preview,
            }
        )
    return json.dumps(items, ensure_ascii=False, indent=2)


def _parse_response(text: str) -> list[dict]:
    """Parse JSON array from Claude's response text."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening and closing fence
        inner = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                inner.append(line)
        text = "\n".join(inner)

    return json.loads(text)


async def curate_posts(posts: list[dict]) -> list[dict]:
    """
    Curate a list of posts using Claude.

    Returns the same list with added keys for posts that should be kept:
        keep (bool), curation_score (int), summary (str), key_insights (list[str])

    Posts not selected by Claude will have keep=False.
    """
    if not posts:
        return posts

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping curation, marking all posts keep=False")
        for post in posts:
            post["keep"] = False
        return posts

    client = anthropic.Anthropic(api_key=api_key)

    # Work on a copy so we don't mutate the caller's list unexpectedly
    result_posts = list(posts)

    # Initialise keep=False for all
    for post in result_posts:
        post.setdefault("keep", False)

    # Process in batches
    for batch_start in range(0, len(result_posts), _BATCH_SIZE):
        batch = result_posts[batch_start : batch_start + _BATCH_SIZE]
        user_msg = _build_user_message(batch)

        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw_text = response.content[0].text
        except Exception as exc:
            logger.error("Claude API error on batch starting at %d: %s", batch_start, exc)
            continue

        try:
            results = _parse_response(raw_text)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Failed to parse Claude JSON response for batch at %d: %s\nRaw: %s",
                batch_start,
                exc,
                raw_text[:500],
            )
            continue

        for item in results:
            try:
                idx = int(item["index"])
                if idx < 0 or idx >= len(batch):
                    logger.warning("Claude returned out-of-range index %d in batch", idx)
                    continue
                post = batch[idx]
                post["keep"] = bool(item.get("keep", False))
                post["curation_score"] = int(item.get("curation_score", 0))
                post["summary"] = str(item.get("summary", ""))
                post["key_insights"] = list(item.get("key_insights", []))
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Error applying curation result item %s: %s", item, exc)
                continue

    return result_posts
