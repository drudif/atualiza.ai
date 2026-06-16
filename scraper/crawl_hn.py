"""Hacker News scraping via Algolia Search API."""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

_ALGOLIA = "https://hn.algolia.com/api/v1"
_MAX_AGE_DAYS = 60
_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text).strip()


def _cutoff_ts() -> int:
    return int((datetime.now(tz=timezone.utc) - timedelta(days=_MAX_AGE_DAYS)).timestamp())


async def search_stories(
    query: str,
    min_points: int = 30,
    min_comments: int = 3,
    max_results: int = 15,
) -> list[dict]:
    url = (
        f"{_ALGOLIA}/search"
        f"?query={query}"
        f"&tags=story"
        f"&numericFilters=created_at_i>{_cutoff_ts()},points>={min_points}"
        f"&hitsPerPage={max_results}"
    )

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("HN Algolia erro em '%s': %s", query, exc)
            return []

    posts = []
    for hit in data.get("hits", []):
        try:
            num_comments = int(hit.get("num_comments", 0))
            if num_comments < min_comments:
                continue

            hn_id = hit.get("objectID", "")
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"

            highlight = hit.get("_highlightResult", {})
            title_matched = highlight.get("title", {}).get("matchedWords", [])
            posts.append({
                "subreddit": "hackernews",
                "title": hit.get("title", ""),
                "url": story_url,
                "score": int(hit.get("points", 0)),
                "num_comments": num_comments,
                "author": hit.get("author"),
                "created_utc": hit.get("created_at"),
                "body_md": _strip_html(hit.get("story_text") or "")[:2000],
                "reddit_id": hn_id,
                "permalink": f"/item?id={hn_id}",
                "hn_id": hn_id,
                "hn_title_matched_words": title_matched,  # palavras da query no título
                "hn_external_url": hit.get("url", ""),    # URL externa (github, youtube, etc.)
                "topic_ids": [],
                "top_comments": [],
            })
        except Exception as exc:
            logger.warning("Erro parseando hit HN: %s", exc)

    logger.info("HN '%s' — %d stories", query, len(posts))
    return posts


async def fetch_comments(hn_id: str, limit: int = 5) -> list[dict]:
    """Fetch story + top comments via Algolia items endpoint (uma requisição)."""
    url = f"{_ALGOLIA}/items/{hn_id}"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug("HN comments erro %s: %s", hn_id, exc)
            return []

    comments = []
    for child in (data.get("children") or [])[:limit]:
        try:
            text = _strip_html(child.get("text") or "")
            if not text or child.get("type") != "comment":
                continue
            comments.append({
                "author": child.get("author", ""),
                "score": 0,
                "body": text[:400],
            })
        except Exception:
            continue

    return comments
