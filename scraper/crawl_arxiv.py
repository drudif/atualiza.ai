"""arXiv scraping via Atom API (cs.CV / cs.GR / cs.AI)."""

import logging
import re
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_ARXIV_API = "http://export.arxiv.org/api/query"
_QUERY = "cat:cs.CV+OR+cat:cs.GR+OR+cat:cs.AI"
_MAX_AGE_DAYS = 60
_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_ATOM = "{http://www.w3.org/2005/Atom}"


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text).strip()


def _collapse(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _cutoff_dt() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=_MAX_AGE_DAYS)


def _parse_published(value: str) -> datetime | None:
    """Parse arXiv <published> (ISO 8601, ex '2024-01-02T18:00:00Z') -> UTC aware."""
    if not value:
        return None
    raw = value.strip()
    try:
        # fromisoformat aceita offset; troca 'Z' por '+00:00'
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    # garante timezone-aware em UTC (evita comparar naive vs aware)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def fetch_recent(max_results: int = 50) -> list[dict]:
    """Busca papers recentes de cs.CV/cs.GR/cs.AI. Filtra por _MAX_AGE_DAYS (60)."""
    url = (
        f"{_ARXIV_API}"
        f"?search_query={_QUERY}"
        f"&sortBy=submittedDate"
        f"&sortOrder=descending"
        f"&max_results={max_results}"
    )

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            text = resp.text
        except Exception as exc:
            logger.warning("arXiv API erro: %s", exc)
            return []

    try:
        root = ET.fromstring(text)
    except Exception as exc:
        logger.warning("arXiv XML parse erro: %s", exc)
        return []

    cutoff = _cutoff_dt()
    posts = []
    for entry in root.findall(f"{_ATOM}entry"):
        try:
            published_el = entry.find(f"{_ATOM}published")
            published = published_el.text if published_el is not None else ""
            pub_dt = _parse_published(published or "")
            if pub_dt is None or pub_dt < cutoff:
                continue

            title_el = entry.find(f"{_ATOM}title")
            title = _collapse(title_el.text or "") if title_el is not None else ""

            summary_el = entry.find(f"{_ATOM}summary")
            abstract = _collapse(_strip_html(summary_el.text or "")) if summary_el is not None else ""

            # <id> é a URL do abstract (https://arxiv.org/abs/XXXX)
            id_el = entry.find(f"{_ATOM}id")
            abs_url = (id_el.text or "").strip() if id_el is not None else ""

            # tenta link rel="alternate"; cai para o id
            for link in entry.findall(f"{_ATOM}link"):
                if link.get("rel") == "alternate" and link.get("href"):
                    abs_url = link.get("href").strip()
                    break

            # primeiro autor
            author = None
            author_el = entry.find(f"{_ATOM}author")
            if author_el is not None:
                name_el = author_el.find(f"{_ATOM}name")
                if name_el is not None and name_el.text:
                    author = name_el.text.strip()

            match_text = f"{title} {abstract}".lower()

            posts.append({
                "subreddit": "arxiv",
                "title": title,
                "url": abs_url,
                "score": 0,
                "num_comments": 0,
                "author": author,
                "created_utc": (published or "").strip(),
                "body_md": abstract[:2000],
                "permalink": abs_url,
                "match_text": match_text,
                "topic_ids": [],
                "top_comments": [],
            })
        except Exception as exc:
            logger.warning("Erro parseando entry arXiv: %s", exc)

    logger.info("arXiv — %d papers recentes", len(posts))
    return posts


async def fetch_comments(post: dict, limit: int = 10) -> list[dict]:
    """arXiv não tem comentários — retorne [] sempre."""
    return []
