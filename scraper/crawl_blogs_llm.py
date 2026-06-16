"""Blog scraping para sites SEM RSS, via render (Crawl4AI) + extração por LLM (Gemini).

Para sites JS-only / sem feed (Adobe, Anthropic, AcademyPass, Runway, Perplexity,
FeedHive): renderiza a página de listagem com Playwright e pede ao Gemini para
extrair os artigos recentes como JSON. Evita parser bespoke por site.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import httpx

import crawl_blogs

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"
_MAX_AGE_DAYS = 60
_WS = re.compile(r"\s+")

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Sites sem RSS de alto fit criativo — `url` é a página renderizada + extraída
# por LLM. `rss_url` (opcional) é tentado ANTES do render (re-teste de feed que
# pode voltar a funcionar, ex: Adobe).
LLM_BLOGS: list[dict] = [
    {"source_id": "adobe", "url": "https://blog.adobe.com/", "rss_url": "https://blog.adobe.com/feed.xml"},
    {"source_id": "runway", "url": "https://runwayml.com/research"},
]

LLM_BLOG_SOURCE_IDS = frozenset(b["source_id"] for b in LLM_BLOGS)

_EXTRACT_PROMPT = """You are extracting blog/article entries from the rendered text of a blog listing page.

Return ONLY a valid JSON array. Each element is an article with:
- title (str): the article headline
- url (str): the article link — make it ABSOLUTE using the page base URL if relative
- date (str|null): publication date in ISO 8601 (YYYY-MM-DD) if visible, else null
- summary (str): a 1-2 sentence description if available, else ""

Rules:
- Only REAL articles/posts. Ignore nav links, categories, footers, "load more", author pages, newsletter signup.
- Max 12 most recent articles.
- No markdown, no commentary — raw JSON array only."""


def _cutoff() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=_MAX_AGE_DAYS)


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _render(url: str) -> str:
    """Renderiza a página com Crawl4AI/Playwright e retorna o markdown."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig  # type: ignore

        browser_cfg = BrowserConfig(headless=True, browser_type="chromium", user_agent=_BROWSER_UA)
        run_cfg = CrawlerRunConfig(js_code="window.scrollTo(0, 1500);", page_timeout=25000)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if not result or not result.success:
            logger.warning("Render falhou para %s: %s", url, getattr(result, "error_message", "?"))
            return ""
        return result.markdown or ""
    except Exception as exc:
        logger.warning("Erro renderizando %s: %s", url, exc)
        return ""


def _extract_articles(client, markdown: str, base_url: str) -> list[dict]:
    """Pede ao Gemini para extrair os artigos do markdown renderizado."""
    from google.genai import types  # lazy

    # Limita o tamanho enviado ao modelo (listagens longas)
    content = f"PAGE BASE URL: {base_url}\n\nRENDERED PAGE:\n{markdown[:18000]}"
    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=_EXTRACT_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        data = json.loads(response.text)
    except Exception as exc:
        logger.warning("Extração LLM falhou para %s: %s", base_url, exc)
        return []
    return data if isinstance(data, list) else []


async def fetch_recent() -> list[dict]:
    """Renderiza + extrai artigos dos blogs sem RSS. Filtra por _MAX_AGE_DAYS (60)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY ausente — pulando blogs sem RSS")
        return []

    from google import genai  # lazy
    client = genai.Client(api_key=api_key)

    cutoff = _cutoff()
    all_posts: list[dict] = []

    for blog in LLM_BLOGS:
        source_id = blog["source_id"]
        base_url = blog["url"]

        # 0. Re-teste de RSS (ex: Adobe) — se voltar a funcionar, usa e pula render+LLM
        rss_url = blog.get("rss_url")
        if rss_url:
            async with httpx.AsyncClient() as rss_client:
                rss_posts = await crawl_blogs._fetch_one(
                    rss_client, {"source_id": source_id, "feed_url": rss_url}
                )
            if rss_posts:
                logger.info("Blog-LLM '%s' — RSS voltou (%d posts), pulou render", source_id, len(rss_posts))
                all_posts.extend(rss_posts)
                continue

        markdown = await _render(base_url)
        if not markdown:
            logger.info("Blog-LLM '%s' — 0 posts (render vazio)", source_id)
            continue

        articles = _extract_articles(client, markdown, base_url)
        kept = 0
        for art in articles:
            try:
                title = _WS.sub(" ", str(art.get("title", ""))).strip()
                url = str(art.get("url", "")).strip()
                if not title or not url:
                    continue
                url = urljoin(base_url, url)  # resolve relativos
                dt = _parse_date(art.get("date"))
                if dt is not None and dt < cutoff:
                    continue  # mais antigo que 60 dias
                summary = _WS.sub(" ", str(art.get("summary", "") or "")).strip()[:2000]
                all_posts.append({
                    "subreddit": source_id,
                    "title": title,
                    "url": url,
                    "score": 0,
                    "num_comments": 0,
                    "author": None,
                    "created_utc": dt.isoformat() if dt else None,
                    "body_md": summary,
                    "permalink": url,
                    "match_text": (title + " " + summary).lower(),
                    "topic_ids": [],
                    "top_comments": [],
                })
                kept += 1
            except Exception:
                continue
        logger.info("Blog-LLM '%s' — %d posts", source_id, kept)
        await asyncio.sleep(1)

    return all_posts


async def fetch_comments(post: dict, limit: int = 10) -> list[dict]:
    """Blogs não têm comentários."""
    return []
