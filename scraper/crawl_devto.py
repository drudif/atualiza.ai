"""Dev.to scraping via API pública (sem auth)."""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

_DEVTO = "https://dev.to/api"
_MAX_AGE_DAYS = 60
_HTML_TAG = re.compile(r"<[^>]+>")

# Tags relevantes a IA criativa.
_TAGS = ["ai", "comfyui", "stablediffusion", "machinelearning", "generativeai"]


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text).strip()


def _cutoff_dt() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=_MAX_AGE_DAYS)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _fetch_tag(client: httpx.AsyncClient, tag: str, per_tag: int) -> list[dict]:
    url = f"{_DEVTO}/articles?tag={tag}&top=7&per_page={per_tag}"
    try:
        resp = await client.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Dev.to erro na tag '%s': %s", tag, exc)
        return []


async def fetch_recent(per_tag: int = 30) -> list[dict]:
    """Busca artigos top-7d das tags de IA criativa, deduplica por id. Filtra por _MAX_AGE_DAYS (60)."""
    cutoff = _cutoff_dt()
    seen: set[int] = set()
    posts: list[dict] = []

    async with httpx.AsyncClient() as client:
        for i, tag in enumerate(_TAGS):
            articles = await _fetch_tag(client, tag, per_tag)
            for art in articles:
                try:
                    art_id = int(art.get("id"))
                    if art_id in seen:
                        continue

                    created_raw = art.get("published_at") or art.get("published_timestamp")
                    created_dt = _parse_dt(created_raw)
                    if created_dt is None or created_dt < cutoff:
                        continue

                    seen.add(art_id)

                    title = art.get("title", "") or ""
                    description = _strip_html(art.get("description") or "")
                    tag_list = art.get("tag_list") or []
                    if isinstance(tag_list, str):
                        tag_list = [tag_list]
                    user = art.get("user") or {}
                    article_url = art.get("url", "") or ""

                    match_text = (
                        title + " " + description + " " + " ".join(tag_list)
                    ).lower()

                    posts.append({
                        "subreddit": "devto",
                        "title": title,
                        "url": article_url,
                        "score": int(art.get("positive_reactions_count", 0) or 0),
                        "num_comments": int(art.get("comments_count", 0) or 0),
                        "author": user.get("name"),
                        "created_utc": created_raw,
                        "body_md": description[:2000],
                        "permalink": article_url,
                        "devto_id": art_id,
                        "match_text": match_text,
                        "topic_ids": [],
                        "top_comments": [],
                    })
                except Exception as exc:
                    logger.warning("Erro parseando artigo Dev.to: %s", exc)

            if i < len(_TAGS) - 1:
                await asyncio.sleep(0.5)

    logger.info("Dev.to — %d artigos", len(posts))
    return posts


async def fetch_comments(post: dict, limit: int = 10) -> list[dict]:
    """GET /comments?a_id=post["devto_id"]. Achata a árvore (comentários de topo).
    Retorna dicts {"author","score":0,"body"} (body strip HTML, máx 400), top `limit`."""
    devto_id = post.get("devto_id")
    if devto_id is None:
        return []

    url = f"{_DEVTO}/comments?a_id={devto_id}"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug("Dev.to comments erro %s: %s", devto_id, exc)
            return []

    comments: list[dict] = []
    for node in (data or [])[:limit]:
        try:
            body = _strip_html(node.get("body_html") or "")
            if not body:
                continue
            user = node.get("user") or {}
            comments.append({
                "author": user.get("name") or user.get("username") or "",
                "score": 0,
                "body": body[:400],
            })
        except Exception:
            continue

    return comments
