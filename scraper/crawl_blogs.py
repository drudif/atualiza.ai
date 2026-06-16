"""Generic RSS/Atom blog scraping for creative-ai-feed.

Lê feeds RSS 2.0 e Atom de publicações selecionadas. Parser namespace-agnóstico
(stdlib xml.etree), sem dependência de feedparser. Mesmo formato de dict das
outras fontes (crawl_hn, crawl_arxiv, ...), com `match_text` para casar tópicos.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_MAX_AGE_DAYS = 60
_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_UA = "creative-ai-feed/1.0 (+https://convert)"

# Registro de blogs com feed RSS/Atom confirmado.
# default_author é usado quando o feed não traz autor por item.
BLOGS: list[dict] = [
    {"source_id": "itsnicethat", "feed_url": "https://www.itsnicethat.com/articles.rss"},
    {"source_id": "kdnuggets", "feed_url": "https://www.kdnuggets.com/feed"},
    {"source_id": "medium", "feed_url": "https://medium.com/feed/tag/artificial-intelligence"},
    {"source_id": "openai", "feed_url": "https://openai.com/news/rss.xml", "default_author": "OpenAI"},
    {"source_id": "googleresearch", "feed_url": "https://research.google/blog/rss/", "default_author": "Google Research"},
    {"source_id": "actuia", "feed_url": "https://www.actuia.com/feed/"},
]

# Usado pelo run.py para rotear o passo de comentários (blogs não têm comentários).
BLOG_SOURCE_IDS = frozenset(b["source_id"] for b in BLOGS)


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", _HTML_TAG.sub(" ", text)).strip()


def _cutoff() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=_MAX_AGE_DAYS)


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    # RFC822 (RSS): "Tue, 16 Jun 2026 08:00:00 GMT"
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    # ISO 8601 (Atom): "2026-06-16T08:00:00Z"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _extract_link(item: ET.Element) -> str:
    """RSS: <link>text</link>. Atom: <link rel="alternate" href="..."/>."""
    fallback = ""
    for child in item:
        if _localname(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            rel = child.attrib.get("rel", "alternate")
            if rel == "alternate":
                return href
            fallback = fallback or href
        elif child.text and child.text.strip():
            return child.text.strip()
    return fallback


def _extract_author(item: ET.Element) -> str | None:
    for child in item:
        name = _localname(child.tag)
        if name == "creator" and child.text:  # dc:creator
            return child.text.strip()
        if name == "author":
            if child.text and child.text.strip():  # RSS <author>
                return child.text.strip()
            for sub in child:  # Atom <author><name>
                if _localname(sub.tag) == "name" and sub.text:
                    return sub.text.strip()
    return None


def _extract_body(item: ET.Element) -> str:
    """Prefere content:encoded > summary > description > content."""
    by_name: dict[str, str] = {}
    for child in item:
        name = _localname(child.tag)
        if name in ("encoded", "summary", "description", "content") and child.text:
            by_name.setdefault(name, child.text)
    for key in ("encoded", "summary", "description", "content"):
        if by_name.get(key):
            return _strip_html(by_name[key])[:2000]
    return ""


def _parse_feed(xml_text: str, source_id: str, default_author: str | None) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Blog '%s' — XML inválido: %s", source_id, exc)
        return []

    cutoff = _cutoff()
    posts: list[dict] = []
    for item in root.iter():
        if _localname(item.tag) not in ("item", "entry"):
            continue

        title = ""
        date_raw = ""
        for child in item:
            cn = _localname(child.tag)
            if cn == "title" and child.text:
                title = _WS.sub(" ", child.text).strip()
            elif cn in ("pubDate", "published", "updated", "date") and child.text and not date_raw:
                date_raw = child.text

        url = _extract_link(item)
        if not title or not url:
            continue

        dt = _parse_date(date_raw)
        if dt is not None and dt < cutoff:
            continue  # mais antigo que 60 dias

        body = _extract_body(item)
        posts.append({
            "subreddit": source_id,
            "title": title,
            "url": url,
            "score": 0,
            "num_comments": 0,
            "author": _extract_author(item) or default_author,
            "created_utc": dt.isoformat() if dt else None,
            "body_md": body,
            "permalink": url,
            "match_text": (title + " " + body).lower(),
            "topic_ids": [],
            "top_comments": [],
        })
    return posts


async def _fetch_one(client: httpx.AsyncClient, blog: dict) -> list[dict]:
    source_id = blog["source_id"]
    try:
        resp = await client.get(blog["feed_url"], headers={"User-Agent": _UA},
                                follow_redirects=True, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Blog '%s' — erro de rede: %s", source_id, exc)
        return []
    posts = _parse_feed(resp.text, source_id, blog.get("default_author"))
    logger.info("Blog '%s' — %d posts", source_id, len(posts))
    return posts


async def fetch_recent() -> list[dict]:
    """Busca todos os blogs do registro. Filtra por _MAX_AGE_DAYS (60)."""
    all_posts: list[dict] = []
    async with httpx.AsyncClient() as client:
        for blog in BLOGS:
            all_posts.extend(await _fetch_one(client, blog))
            await asyncio.sleep(0.5)
    return all_posts


async def fetch_comments(post: dict, limit: int = 10) -> list[dict]:
    """Blogs não têm comentários."""
    return []
