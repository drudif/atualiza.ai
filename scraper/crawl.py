"""Reddit scraping for creative-ai-feed.

Strategy (in order):
1. Reddit JSON API with browser-like UA (fast, no JS needed)
2. old.reddit.com JSON API (often less restricted)
3. Crawl4AI + Playwright (full browser, extracts embedded __NEXT_DATA__ JSON)
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "config" / "subreddits.yaml"

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "application/json, text/javascript, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def _thresholds() -> dict:
    return _load_config().get("engagement_threshold", {})


def _parse_utc(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return None


async def _try_json_api(client: httpx.AsyncClient, url: str) -> dict | list | None:
    try:
        resp = await client.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code == 429:
            logger.warning("Rate limited (429) for %s — sleeping 5s", url)
            await asyncio.sleep(5)
            resp = await client.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("HTTP %d for %s", resp.status_code, url)
    except Exception as exc:
        logger.warning("Request error for %s: %s", url, exc)
    return None


def _extract_posts_from_listing(data: dict | list, subreddit: str, min_score: int, min_comments: int) -> list[dict]:
    posts: list[dict] = []
    try:
        if isinstance(data, list):
            data = data[0]
        children = data["data"]["children"]
    except (KeyError, TypeError, IndexError):
        logger.error("Unexpected listing JSON structure for r/%s", subreddit)
        return posts

    for child in children:
        try:
            p = child["data"]
            score = int(p.get("score", 0))
            num_comments = int(p.get("num_comments", 0))
            if score < min_score or num_comments < min_comments:
                continue

            permalink = p.get("permalink", "")
            post_url = f"https://www.reddit.com{permalink}" if permalink else p.get("url", "")

            body_md = ""
            selftext = p.get("selftext", "")
            if selftext and selftext not in ("[removed]", "[deleted]"):
                body_md = selftext[:2000]

            posts.append({
                "subreddit": subreddit,
                "title": p.get("title", ""),
                "url": post_url,
                "score": score,
                "num_comments": num_comments,
                "author": p.get("author"),
                "created_utc": _parse_utc(p.get("created_utc")),
                "body_md": body_md,
                "reddit_id": p.get("id", ""),
                "permalink": permalink,
                "topic_ids": [],
                "top_comments": [],
            })
        except Exception as exc:
            logger.warning("Error parsing post in r/%s: %s", subreddit, exc)
    return posts


async def _crawl4ai_fetch(subreddit: str) -> list[dict]:
    """Use Crawl4AI + Playwright to scrape Reddit when JSON API is blocked.
    Extracts posts from the embedded __NEXT_DATA__ JSON in the page."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig  # type: ignore

        url = f"https://www.reddit.com/r/{subreddit}/top/?t=week"

        browser_cfg = BrowserConfig(
            headless=True,
            browser_type="chromium",
            user_agent=_BROWSER_UA,
        )
        run_cfg = CrawlerRunConfig(
            js_code="window.scrollTo(0, 500);",
            wait_for="css:shreddit-post",
            page_timeout=20000,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if not result or not result.success:
            logger.warning("Crawl4AI failed for r/%s: %s", subreddit, getattr(result, "error_message", "unknown"))
            return []

        html = result.html or ""
        posts = _parse_next_data(html, subreddit)

        if not posts:
            # Fallback: try to parse shreddit post elements from markdown
            posts = _parse_markdown_posts(result.markdown or "", subreddit)

        logger.info("Crawl4AI scraped %d posts from r/%s", len(posts), subreddit)
        return posts

    except Exception as exc:
        logger.error("Crawl4AI error for r/%s: %s", subreddit, exc)
        return []


def _parse_next_data(html: str, subreddit: str) -> list[dict]:
    """Extract posts from Reddit's embedded __NEXT_DATA__ JSON."""
    thresh = _thresholds()
    min_score = thresh.get("min_score", 20)
    min_comments = thresh.get("min_comments", 3)

    match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
        # Navigate Reddit's Next.js state
        posts_data = (
            data.get("props", {})
            .get("pageProps", {})
            .get("postsFromSubreddit", [])
        )
        if not posts_data:
            return []
    except Exception:
        return []

    posts: list[dict] = []
    for p in posts_data:
        try:
            score = int(p.get("score", 0))
            num_comments = int(p.get("numComments", p.get("num_comments", 0)))
            if score < min_score or num_comments < min_comments:
                continue
            permalink = p.get("permalink", "")
            posts.append({
                "subreddit": subreddit,
                "title": p.get("title", ""),
                "url": f"https://www.reddit.com{permalink}" if permalink else "",
                "score": score,
                "num_comments": num_comments,
                "author": p.get("author", {}).get("name") if isinstance(p.get("author"), dict) else p.get("author"),
                "created_utc": _parse_utc(p.get("created", p.get("created_utc"))),
                "body_md": p.get("selftext", "")[:2000],
                "reddit_id": p.get("id", ""),
                "permalink": permalink,
                "topic_ids": [],
                "top_comments": [],
            })
        except Exception:
            continue
    return posts


def _parse_markdown_posts(markdown: str, subreddit: str) -> list[dict]:
    """Last-resort: extract post titles and links from rendered markdown."""
    posts: list[dict] = []
    # Look for patterns like [title](https://www.reddit.com/r/subreddit/comments/...)
    pattern = re.compile(
        r'\[([^\]]{10,200})\]\((https://www\.reddit\.com/r/[^/]+/comments/[^\s)]+)\)'
    )
    seen = set()
    for m in pattern.finditer(markdown):
        title, url = m.group(1), m.group(2)
        if url in seen:
            continue
        seen.add(url)
        posts.append({
            "subreddit": subreddit,
            "title": title,
            "url": url,
            "score": 0,
            "num_comments": 0,
            "author": None,
            "created_utc": None,
            "body_md": "",
            "reddit_id": "",
            "permalink": url.replace("https://www.reddit.com", ""),
            "topic_ids": [],
            "top_comments": [],
        })
        if len(posts) >= 25:
            break
    return posts


async def fetch_top_posts(subreddit: str, limit: int = 25) -> list[dict]:
    thresh = _thresholds()
    min_score = thresh.get("min_score", 20)
    min_comments = thresh.get("min_comments", 3)

    urls = [
        f"https://www.reddit.com/r/{subreddit}/top.json?t=week&limit={limit}&raw_json=1",
        f"https://old.reddit.com/r/{subreddit}/top.json?t=week&limit={limit}&raw_json=1",
    ]

    async with httpx.AsyncClient() as client:
        for url in urls:
            data = await _try_json_api(client, url)
            if data:
                posts = _extract_posts_from_listing(data, subreddit, min_score, min_comments)
                logger.info("r/%s — %d posts via JSON API", subreddit, len(posts))
                return posts
            await asyncio.sleep(1)

    logger.warning("JSON API blocked for r/%s — using Crawl4AI+Playwright", subreddit)
    posts = await _crawl4ai_fetch(subreddit)
    filtered = [p for p in posts if p["score"] >= min_score or p["score"] == 0]
    logger.info("r/%s — %d posts via Crawl4AI", subreddit, len(filtered))
    return filtered


async def fetch_top_comments(permalink: str, limit: int = 10) -> list[dict]:
    if not permalink.startswith("/"):
        permalink = "/" + permalink

    urls = [
        f"https://www.reddit.com{permalink}.json?limit=100&sort=top&raw_json=1",
        f"https://old.reddit.com{permalink}.json?limit=100&sort=top&raw_json=1",
    ]

    async with httpx.AsyncClient() as client:
        for url in urls:
            data = await _try_json_api(client, url)
            if data:
                break
            await asyncio.sleep(0.5)

    if not data:
        return []

    comments: list[dict] = []
    try:
        if not isinstance(data, list) or len(data) < 2:
            return []
        children = data[1]["data"]["children"]
    except (KeyError, TypeError, IndexError):
        return []

    for child in children:
        try:
            if child.get("kind") != "t1":
                continue
            c = child["data"]
            body = c.get("body", "")
            if body in ("[removed]", "[deleted]", ""):
                continue
            comments.append({
                "author": c.get("author"),
                "score": int(c.get("score", 0)),
                "body": body,
            })
        except Exception:
            continue

    comments.sort(key=lambda x: x["score"], reverse=True)
    return comments[:limit]
