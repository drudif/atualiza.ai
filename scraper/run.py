"""Entry point for creative-ai-feed scraper pipeline."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv

import crawl
import crawl_hn
import crawl_arxiv
import crawl_lobsters
import crawl_devto
import crawl_blogs
import crawl_blogs_llm
import curate
import slop_filter
import store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Suprimir logs verbose de bibliotecas externas
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("crawl4ai").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = typer.Typer()

_SCRAPER_DIR = Path(__file__).parent
_CONFIG_PATH = _SCRAPER_DIR / "config" / "subreddits.yaml"

# Palavras genéricas que não diferenciam tópico — ignorar no match de query
_HN_STOPWORDS = {
    "ai", "a", "an", "the", "of", "in", "for", "with", "how", "to", "and",
    "or", "new", "using", "my", "your", "our", "its", "on", "at", "by",
}


def _hn_matches_topic(post: dict, topic: dict, query: str) -> bool:
    """Retorna True se o post HN é genuinamente relevante para o tópico.

    Usa título, URL externa e palavras da query encontradas no título (Algolia
    _highlightResult) — não o body/text, para evitar matches superficiais.
    """
    title = (post.get("title") or "").lower()
    ext_url = (post.get("hn_external_url") or "").lower()
    searchable = title + " " + ext_url

    # 1. Qualquer keyword do tópico no título ou URL externa
    for kw in topic.get("keywords", []):
        if kw.lower() in searchable:
            return True

    # 2. Palavras significativas da query encontradas especificamente no título
    q_words = [w.lower() for w in query.split() if w.lower() not in _HN_STOPWORDS]
    if not q_words:
        return True  # query só tinha stopwords, aceita tudo

    title_matched = {w.lower() for w in (post.get("hn_title_matched_words") or [])}
    matches = [w for w in q_words if w in title_matched or w in title]
    # Exige pelo menos 1 palavra significativa no título
    return len(matches) >= 1


def _match_topics_by_keywords(post: dict, topics: list[dict]) -> list[str]:
    """Casa um post de fonte global (arXiv/Lobsters/Dev.to) com tópicos via keywords.

    Usa o `match_text` do post (title + body + tags, lowercased) contra as
    keywords de cada tópico. Retorna todos os topic_ids que casaram.
    """
    text = (post.get("match_text") or "").lower()
    if not text:
        text = (post.get("title", "") + " " + (post.get("body_md") or "")).lower()
    matched: list[str] = []
    for topic in topics:
        for kw in topic.get("keywords", []):
            if kw.lower() in text:
                matched.append(topic.get("id", ""))
                break
    return matched


def _load_env() -> None:
    """Load .env from parent directory and scraper directory."""
    parent_env = _SCRAPER_DIR.parent / ".env"
    local_env = _SCRAPER_DIR / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
        logger.info("Loaded .env from %s", parent_env)
    if local_env.exists():
        load_dotenv(local_env, override=True)
        logger.info("Loaded .env from %s", local_env)


def _load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _week_label() -> str:
    """Return ISO week label for today, e.g. '2026-W24'."""
    now = datetime.now(tz=timezone.utc)
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


async def _run(dry_run: bool = False) -> None:
    _load_env()

    # 1. Init DB
    await store.init_db()

    # 2. Create run record
    run_id = await store.create_run()
    logger.info("Created run id=%d", run_id)

    # 3. Load config
    config = _load_config()
    topics: list[dict] = config.get("topics", [])
    thresh = config.get("engagement_threshold", {})
    comment_limit: int = thresh.get("top_comments", 10)
    top_posts_per_sub: int = thresh.get("top_posts_per_sub", 25)

    # 4. Collect all posts — url -> post, url -> topic_ids
    url_to_post: dict[str, dict] = {}
    url_to_topics: dict[str, list[str]] = {}

    def _register(post: dict, topic_id: str) -> None:
        url = post["url"]
        if url not in url_to_topics:
            url_to_topics[url] = []
        if topic_id not in url_to_topics[url]:
            url_to_topics[url].append(topic_id)
        if url not in url_to_post:
            url_to_post[url] = post

    # 4a. Reddit
    fetched_subs: dict[str, list[dict]] = {}
    for topic in topics:
        topic_id: str = topic.get("id", "")
        for subreddit in topic.get("subreddits", []):
            if subreddit in fetched_subs:
                logger.info("r/%s — cache hit", subreddit)
                sub_posts = fetched_subs[subreddit]
            else:
                logger.info("Scraping r/%s (tópico '%s')", subreddit, topic_id)
                try:
                    sub_posts = await crawl.fetch_top_posts(subreddit, limit=top_posts_per_sub)
                except Exception as exc:
                    logger.error("Erro buscando r/%s: %s", subreddit, exc)
                    sub_posts = []
                fetched_subs[subreddit] = sub_posts
                await asyncio.sleep(2.5 + (len(fetched_subs) % 3) * 0.5)

            for post in sub_posts:
                _register(post, topic_id)

    # 4b. Hacker News
    fetched_hn: dict[str, list[dict]] = {}
    for topic in topics:
        topic_id = topic.get("id", "")
        for query in topic.get("hn_queries", []):
            if query in fetched_hn:
                hn_posts = fetched_hn[query]
            else:
                logger.info("HN query '%s' (tópico '%s')", query, topic_id)
                try:
                    hn_posts = await crawl_hn.search_stories(query)
                except Exception as exc:
                    logger.error("Erro HN '%s': %s", query, exc)
                    hn_posts = []
                fetched_hn[query] = hn_posts
                await asyncio.sleep(1.5)

            for post in hn_posts:
                if _hn_matches_topic(post, topic, query):
                    _register(post, topic_id)
                else:
                    logger.debug("HN '%s' descartado para '%s': título irrelevante", post.get("title", "")[:60], topic_id)

    # 4c. Fontes adicionais (arXiv, Lobsters, Dev.to) — busca global única por
    # fonte; cada post é casado com tópicos pelas keywords. Posts que não casam
    # com nenhum tópico são descartados (feeds amplos, só queremos o relevante).
    extra_sources = [
        ("arXiv", crawl_arxiv.fetch_recent),
        ("Lobsters", crawl_lobsters.fetch_recent),
        ("Dev.to", crawl_devto.fetch_recent),
    ]
    for source_name, fetch_fn in extra_sources:
        logger.info("Buscando fonte '%s'", source_name)
        try:
            src_posts = await fetch_fn()
        except Exception as exc:
            logger.error("Erro buscando %s: %s", source_name, exc)
            src_posts = []

        matched_count = 0
        for post in src_posts:
            matched_topics = _match_topics_by_keywords(post, topics)
            if not matched_topics:
                continue
            for tid in matched_topics:
                _register(post, tid)
            matched_count += 1
        logger.info("%s — %d/%d posts casaram com tópicos", source_name, matched_count, len(src_posts))
        await asyncio.sleep(1)

    # 4d. Blogs (RSS) — publicações selecionadas pelo usuário. Casa por keyword,
    # mas com FALLBACK para 'general' (são fontes curadas; deixamos a curadoria
    # decidir, em vez de descartar por não bater keyword).
    logger.info("Buscando blogs (RSS)")
    try:
        blog_posts = await crawl_blogs.fetch_recent()
    except Exception as exc:
        logger.error("Erro buscando blogs: %s", exc)
        blog_posts = []
    for post in blog_posts:
        matched_topics = _match_topics_by_keywords(post, topics) or ["general"]
        for tid in matched_topics:
            _register(post, tid)
    logger.info("Blogs — %d posts registrados", len(blog_posts))

    # 4e. Blogs sem RSS (render + LLM): Runway, Adobe. Mesmo fallback p/ 'general'.
    logger.info("Buscando blogs sem RSS (render + LLM)")
    try:
        llm_blog_posts = await crawl_blogs_llm.fetch_recent()
    except Exception as exc:
        logger.error("Erro buscando blogs render+LLM: %s", exc)
        llm_blog_posts = []
    for post in llm_blog_posts:
        matched_topics = _match_topics_by_keywords(post, topics) or ["general"]
        for tid in matched_topics:
            _register(post, tid)
    logger.info("Blogs render+LLM — %d posts registrados", len(llm_blog_posts))

    # 5. For each unique URL, cross-run dedup via DB
    all_posts: list[dict] = []
    for url, post in url_to_post.items():
        if await store.url_exists(url):
            logger.debug("Skipping already-stored URL: %s", url)
            continue
        post["topic_ids"] = url_to_topics.get(url, [])
        all_posts.append(post)

    posts_scraped = len(all_posts)
    logger.info("Total unique new posts: %d", posts_scraped)

    if not all_posts:
        logger.info("No new posts to process.")
        await store.finish_run(run_id, "done", 0, 0)
        typer.echo("Run complete: 0 scraped, 0 curated")
        return

    # 6. Fetch comments — roteado por fonte
    for post in all_posts:
        src = post.get("subreddit")
        try:
            if src == "hackernews":
                hn_id = post.get("hn_id") or post.get("reddit_id", "")
                post["top_comments"] = await crawl_hn.fetch_comments(hn_id, limit=comment_limit) if hn_id else []
                await asyncio.sleep(0.5)
            elif src == "arxiv":
                post["top_comments"] = []  # arXiv não tem comentários
            elif src == "lobsters":
                post["top_comments"] = await crawl_lobsters.fetch_comments(post, limit=comment_limit)
                await asyncio.sleep(0.5)
            elif src == "devto":
                post["top_comments"] = await crawl_devto.fetch_comments(post, limit=comment_limit)
                await asyncio.sleep(0.5)
            elif src in crawl_blogs.BLOG_SOURCE_IDS or src in crawl_blogs_llm.LLM_BLOG_SOURCE_IDS:
                post["top_comments"] = []  # blogs não têm comentários
            else:
                permalink = post.get("permalink", "")
                post["top_comments"] = await crawl.fetch_top_comments(permalink, limit=comment_limit) if permalink else []
                await asyncio.sleep(2 + (hash(permalink) % 10) * 0.1)
        except Exception as exc:
            logger.warning("Erro buscando comentários para '%s': %s", post.get("title", ""), exc)
            post["top_comments"] = []

    # 6b. Filtro anti-slop (heurística, sem custo de API). Roda DEPOIS de buscar
    # comentários (o sinal da comunidade é essencial) e ANTES de salvar/curar.
    kept_posts: list[dict] = []
    slop_removed = 0
    for post in all_posts:
        try:
            eh_slop, slop_score, razoes = slop_filter.is_slop(post)
        except Exception as exc:
            logger.warning("Erro no filtro de slop para '%s': %s", post.get("title", ""), exc)
            kept_posts.append(post)
            continue
        if eh_slop:
            slop_removed += 1
            logger.info(
                "Removido por slop (score=%.2f): '%s' — %s",
                slop_score,
                (post.get("title", "") or "")[:80],
                " | ".join(razoes) if razoes else "sem razões detalhadas",
            )
        else:
            kept_posts.append(post)

    if slop_removed:
        logger.info("%d post(s) removido(s) por slop", slop_removed)
    all_posts = kept_posts
    posts_scraped = len(all_posts)

    if not all_posts:
        logger.info("Nenhum post restante após o filtro de slop.")
        await store.finish_run(run_id, "done", 0, 0)
        typer.echo("Run complete: 0 scraped, 0 curated")
        return

    if dry_run:
        typer.echo(f"[dry-run] Scraped {posts_scraped} posts. Skipping save & curation.")
        await store.finish_run(run_id, "done", posts_scraped, 0)
        return

    # 7. Save all posts, collect db IDs
    post_id_map: dict[str, int] = {}  # url -> db post id
    for post in all_posts:
        try:
            db_id = await store.save_post(post, run_id)
            post_id_map[post["url"]] = db_id
        except Exception as exc:
            logger.error("Error saving post '%s': %s", post.get("title", ""), exc)

    # 8. Curate in batches of 10
    try:
        curated_posts = await curate.curate_posts(all_posts)
    except Exception as exc:
        logger.error("Curation failed: %s", exc)
        await store.finish_run(run_id, "failed", posts_scraped, 0)
        raise typer.Exit(code=1)

    # 9. Persist curation results for kept posts
    curated_post_ids: list[int] = []
    for post in curated_posts:
        if not post.get("keep"):
            continue
        url = post["url"]
        db_id = post_id_map.get(url)
        if db_id is None:
            logger.warning("No db id for curated post url=%s, skipping", url)
            continue
        try:
            await store.update_post_curation(
                db_id,
                curation_score=post.get("curation_score", 0),
                summary=post.get("summary", ""),
                key_insights=post.get("key_insights", []),
            )
            await store.mark_post_curated(db_id)
            curated_post_ids.append(db_id)
        except Exception as exc:
            logger.error("Error updating curation for post id=%d: %s", db_id, exc)

    posts_curated = len(curated_post_ids)

    # 10. Create digest
    week_label = _week_label()
    try:
        await store.create_digest(run_id, week_label, curated_post_ids)
        logger.info("Created digest for %s with %d posts", week_label, posts_curated)
    except Exception as exc:
        logger.error("Error creating digest: %s", exc)

    # 11. Finish run
    await store.finish_run(run_id, "done", posts_scraped, posts_curated)
    typer.echo(f"Run complete: {posts_scraped} scraped, {posts_curated} curated")


@app.command()
def main(
    dry_run: bool = typer.Option(False, "--dry-run", help="Scrape but don't curate or save"),
) -> None:
    """Run the creative-ai-feed scraper pipeline."""
    asyncio.run(_run(dry_run=dry_run))


if __name__ == "__main__":
    app()
