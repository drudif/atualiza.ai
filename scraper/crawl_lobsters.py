"""Lobsters (lobste.rs) scraping via JSON público (sem auth)."""

import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://lobste.rs"
_TAG_URLS = [
    f"{_BASE}/t/ai.json",
    f"{_BASE}/t/ai,ml.json",
]
_MAX_AGE_DAYS = 60
_HTML_TAG = re.compile(r"<[^>]+>")
_HEADERS = {"User-Agent": "creative-ai-feed/1.0"}


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text).strip()


def _cutoff_dt() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=_MAX_AGE_DAYS)


def _parse_created(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _username(user) -> str | None:
    """submitter_user/commenting_user pode ser str OU dict com 'username'."""
    if isinstance(user, dict):
        return user.get("username")
    if isinstance(user, str):
        return user or None
    return None


async def fetch_recent(max_results: int = 40) -> list[dict]:
    """Busca stories recentes das tags ai/ml. Filtra por _MAX_AGE_DAYS (60). Deduplica por short_id_url."""
    cutoff = _cutoff_dt()
    seen: set[str] = set()
    posts: list[dict] = []

    async with httpx.AsyncClient(headers=_HEADERS) as client:
        for url in _TAG_URLS:
            try:
                resp = await client.get(url, timeout=15)
                resp.raise_for_status()
                stories = resp.json()
            except Exception as exc:
                logger.warning("Lobsters erro em '%s': %s", url, exc)
                continue

            if not isinstance(stories, list):
                continue

            for story in stories:
                try:
                    short_id_url = story.get("short_id_url") or ""
                    if short_id_url and short_id_url in seen:
                        continue

                    created_raw = story.get("created_at") or ""
                    created_dt = _parse_created(created_raw)
                    if created_dt is not None and created_dt < cutoff:
                        continue

                    if short_id_url:
                        seen.add(short_id_url)

                    external_url = story.get("url") or ""
                    final_url = external_url or short_id_url

                    body_raw = story.get("description") or story.get("description_plain") or ""
                    body = _strip_html(body_raw)[:2000]

                    tags = story.get("tags") or []
                    tags_text = " ".join(t for t in tags if isinstance(t, str))
                    title = story.get("title", "") or ""
                    match_text = f"{title} {body} {tags_text}".lower()

                    posts.append({
                        "subreddit": "lobsters",
                        "title": title,
                        "url": final_url,
                        "score": int(story.get("score", 0) or 0),
                        "num_comments": int(story.get("comment_count", 0) or 0),
                        "author": _username(story.get("submitter_user")),
                        "created_utc": created_raw,
                        "body_md": body,
                        "permalink": story.get("comments_url") or short_id_url,
                        "match_text": match_text,
                        "topic_ids": [],
                        "top_comments": [],
                    })

                    if len(posts) >= max_results:
                        break
                except Exception as exc:
                    logger.warning("Erro parseando story Lobsters: %s", exc)

            if len(posts) >= max_results:
                break

    logger.info("Lobsters — %d stories", len(posts))
    return posts


async def fetch_comments(post: dict, limit: int = 10) -> list[dict]:
    """Busca top comentários da página da story via comments_url (.json)."""
    permalink = post.get("permalink") or ""
    if not permalink:
        return []

    url = permalink if permalink.endswith(".json") else f"{permalink}.json"

    async with httpx.AsyncClient(headers=_HEADERS) as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug("Lobsters comments erro %s: %s", url, exc)
            return []

    comments = []
    for raw in (data.get("comments") or []):
        try:
            body_raw = raw.get("comment") or raw.get("comment_plain") or ""
            body = _strip_html(body_raw)
            if not body:
                continue
            comments.append({
                "author": _username(raw.get("commenting_user")),
                "score": int(raw.get("score", 0) or 0),
                "body": body[:400],
            })
        except Exception:
            continue

    comments.sort(key=lambda c: c["score"], reverse=True)
    return comments[:limit]
