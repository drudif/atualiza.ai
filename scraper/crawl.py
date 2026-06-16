"""Reddit scraping for creative-ai-feed using httpx JSON API with Crawl4AI fallback."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "config" / "subreddits.yaml"

_HEADERS = {
    "User-Agent": "creative-ai-feed/0.1 by anthropic-agent",
    "Accept": "application/json",
}

# Loaded lazily on first use
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def _thresholds() -> dict:
    cfg = _load_config()
    return cfg.get("engagement_threshold", {})


async def _httpx_get(url: str, client: httpx.AsyncClient) -> dict | list | None:
    """Perform a GET with Reddit-friendly headers. Returns parsed JSON or None on error."""
    try:
        resp = await client.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code == 429:
            logger.warning("Rate limited by Reddit on %s (429), sleeping 5s…", url)
            await asyncio.sleep(5)
            resp = await client.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code != 200:
            logger.warning("Non-200 response %d for %s", resp.status_code, url)
            return None
        return resp.json()
    except Exception as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
        return None


async def _crawl4ai_fallback(url: str) -> str | None:
    """Use Crawl4AI to fetch page content as markdown when JSON API fails."""
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            if result and result.success:
                return result.markdown
    except Exception as exc:
        logger.error("Crawl4AI fallback failed for %s: %s", url, exc)
    return None


async def fetch_top_posts(subreddit: str, limit: int = 25) -> list[dict]:
    """
    Fetch top posts from a subreddit over the past week via Reddit's JSON API.

    Returns a list of post dicts with keys:
        subreddit, title, url, score, num_comments, author, created_utc,
        body_md, reddit_id, permalink
    """
    thresh = _thresholds()
    min_score: int = thresh.get("min_score", 20)
    min_comments: int = thresh.get("min_comments", 3)

    api_url = (
        f"https://www.reddit.com/r/{subreddit}/top.json"
        f"?t=week&limit={limit}&raw_json=1"
    )

    async with httpx.AsyncClient() as client:
        data = await _httpx_get(api_url, client)

    posts: list[dict] = []

    if data is None:
        logger.warning("No data from Reddit JSON API for r/%s, trying Crawl4AI fallback", subreddit)
        # Fallback: return empty — Crawl4AI can't easily parse post listings
        return posts

    children = []
    try:
        children = data["data"]["children"]
    except (KeyError, TypeError):
        logger.error("Unexpected Reddit JSON structure for r/%s", subreddit)
        return posts

    for child in children:
        try:
            p = child["data"]
            score: int = int(p.get("score", 0))
            num_comments: int = int(p.get("num_comments", 0))

            if score < min_score or num_comments < min_comments:
                continue

            reddit_id: str = p.get("id", "")
            permalink: str = p.get("permalink", "")

            # Prefer the Reddit post URL (canonical permalink) as the dedup key
            post_url = f"https://www.reddit.com{permalink}" if permalink else p.get("url", "")

            body_md: str = ""
            selftext = p.get("selftext", "")
            if selftext and selftext not in ("[removed]", "[deleted]"):
                body_md = selftext

            created_utc = p.get("created_utc")
            if created_utc is not None:
                from datetime import datetime, timezone
                created_utc = datetime.fromtimestamp(float(created_utc), tz=timezone.utc).isoformat()

            posts.append(
                {
                    "subreddit": subreddit,
                    "title": p.get("title", ""),
                    "url": post_url,
                    "score": score,
                    "num_comments": num_comments,
                    "author": p.get("author"),
                    "created_utc": created_utc,
                    "body_md": body_md,
                    "reddit_id": reddit_id,
                    "permalink": permalink,
                    # topic_ids populated by run.py
                    "topic_ids": [],
                    # top_comments populated later by fetch_top_comments
                    "top_comments": [],
                }
            )
        except Exception as exc:
            logger.warning("Error parsing post in r/%s: %s", subreddit, exc)
            continue

    logger.info("r/%s — %d posts passed filters (score>=%d, comments>=%d)", subreddit, len(posts), min_score, min_comments)
    return posts


async def fetch_top_comments(permalink: str, limit: int = 10) -> list[dict]:
    """
    Fetch top-level comments for a Reddit post.

    Args:
        permalink: Reddit post path, e.g. "/r/midjourney/comments/abc123/..."
        limit: Maximum number of comments to return (sorted by score desc)

    Returns:
        List of {author, score, body} dicts.
    """
    # Ensure permalink starts with /
    if not permalink.startswith("/"):
        permalink = "/" + permalink

    api_url = f"https://www.reddit.com{permalink}.json?limit=100&sort=top&raw_json=1"

    async with httpx.AsyncClient() as client:
        data = await _httpx_get(api_url, client)

    comments: list[dict] = []

    if data is None:
        return comments

    # Reddit returns a list: [post_listing, comments_listing]
    try:
        if not isinstance(data, list) or len(data) < 2:
            return comments
        comments_listing = data[1]
        children = comments_listing["data"]["children"]
    except (KeyError, TypeError, IndexError) as exc:
        logger.warning("Unexpected comment JSON structure for %s: %s", permalink, exc)
        return comments

    for child in children:
        try:
            kind = child.get("kind", "")
            if kind != "t1":
                continue  # skip "more" entries and non-comments
            c = child["data"]
            body = c.get("body", "")
            if body in ("[removed]", "[deleted]", ""):
                continue
            comments.append(
                {
                    "author": c.get("author"),
                    "score": int(c.get("score", 0)),
                    "body": body,
                }
            )
        except Exception as exc:
            logger.warning("Error parsing comment: %s", exc)
            continue

    # Sort by score descending, take top N
    comments.sort(key=lambda x: x["score"], reverse=True)
    return comments[:limit]
