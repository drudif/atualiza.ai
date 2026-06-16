"""Entry point for creative-ai-feed scraper pipeline."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv

import crawl
import curate
import store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = typer.Typer()

_SCRAPER_DIR = Path(__file__).parent
_CONFIG_PATH = _SCRAPER_DIR / "config" / "subreddits.yaml"


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

    # 4. Collect all posts, deduplicating by URL
    # seen_urls: in-memory set for within-run dedup (DB check for cross-run dedup)
    seen_urls: set[str] = set()
    # Map url -> post dict (most recent topic_ids win if same url appears in multiple topics)
    url_to_post: dict[str, dict] = {}
    url_to_topics: dict[str, list[str]] = {}

    for topic in topics:
        topic_id: str = topic.get("id", "")
        subreddits: list[str] = topic.get("subreddits", [])

        for subreddit in subreddits:
            logger.info("Scraping r/%s for topic '%s'", subreddit, topic_id)
            try:
                posts = await crawl.fetch_top_posts(subreddit, limit=top_posts_per_sub)
            except Exception as exc:
                logger.error("Error fetching r/%s: %s", subreddit, exc)
                posts = []

            for post in posts:
                url = post["url"]
                if url not in url_to_topics:
                    url_to_topics[url] = []
                if topic_id not in url_to_topics[url]:
                    url_to_topics[url].append(topic_id)

                if url not in url_to_post:
                    url_to_post[url] = post

            # Rate limit between subreddit calls
            await asyncio.sleep(1)

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

    # 6. Fetch comments for each post
    for post in all_posts:
        permalink = post.get("permalink", "")
        if permalink:
            try:
                comments = await crawl.fetch_top_comments(permalink, limit=comment_limit)
                post["top_comments"] = comments
            except Exception as exc:
                logger.warning("Error fetching comments for %s: %s", permalink, exc)
                post["top_comments"] = []
        else:
            post["top_comments"] = []
        # Rate limit between comment fetches
        await asyncio.sleep(1)

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
