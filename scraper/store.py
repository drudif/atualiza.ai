"""Async SQLite storage operations for creative-ai-feed scraper."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

# DB path from env var, fallback to ../db/feed.db relative to this file
_DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "db" / "feed.db")
DB_PATH = os.getenv("DB_PATH", _DEFAULT_DB_PATH)

_CREATE_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    posts_scraped INTEGER DEFAULT 0,
    posts_curated INTEGER DEFAULT 0
);
"""

_CREATE_POSTS = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    subreddit TEXT NOT NULL,
    topic_ids TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    score INTEGER NOT NULL,
    num_comments INTEGER NOT NULL,
    author TEXT,
    created_utc TEXT,
    body_md TEXT,
    top_comments TEXT,
    is_curated INTEGER DEFAULT 0,
    curation_score INTEGER,
    summary TEXT,
    key_insights TEXT
);
"""

_CREATE_DIGESTS = """
CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    week_label TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    post_ids TEXT NOT NULL
);
"""


def _db_path() -> str:
    """Return the DB path, re-reading env var each call to support late binding."""
    return os.getenv("DB_PATH", _DEFAULT_DB_PATH)


async def init_db() -> None:
    """Create tables if they don't exist. Also ensures the DB directory exists."""
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute(_CREATE_RUNS)
        await db.execute(_CREATE_POSTS)
        await db.execute(_CREATE_DIGESTS)
        await db.commit()


async def create_run() -> int:
    """Insert a new run record and return its id."""
    started_at = datetime.utcnow().isoformat()
    async with aiosqlite.connect(_db_path()) as db:
        cursor = await db.execute(
            "INSERT INTO runs (started_at, status) VALUES (?, 'running')",
            (started_at,),
        )
        await db.commit()
        return cursor.lastrowid


async def finish_run(
    run_id: int,
    status: str,
    posts_scraped: int,
    posts_curated: int,
) -> None:
    """Mark a run as finished with final stats."""
    finished_at = datetime.utcnow().isoformat()
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            UPDATE runs
            SET finished_at = ?, status = ?, posts_scraped = ?, posts_curated = ?
            WHERE id = ?
            """,
            (finished_at, status, posts_scraped, posts_curated, run_id),
        )
        await db.commit()


async def url_exists(url: str) -> bool:
    """Return True if a post with this URL already exists in the DB."""
    async with aiosqlite.connect(_db_path()) as db:
        async with db.execute(
            "SELECT 1 FROM posts WHERE url = ? LIMIT 1", (url,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def save_post(post: dict, run_id: int) -> int:
    """Insert a post record and return its id."""
    topic_ids = json.dumps(post.get("topic_ids", []))
    top_comments = json.dumps(post.get("top_comments", []))

    async with aiosqlite.connect(_db_path()) as db:
        cursor = await db.execute(
            """
            INSERT INTO posts (
                run_id, subreddit, topic_ids, title, url, score, num_comments,
                author, created_utc, body_md, top_comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                post.get("subreddit", ""),
                topic_ids,
                post.get("title", ""),
                post.get("url", ""),
                post.get("score", 0),
                post.get("num_comments", 0),
                post.get("author"),
                post.get("created_utc"),
                post.get("body_md"),
                top_comments,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def update_post_curation(
    post_id: int,
    curation_score: int,
    summary: str,
    key_insights: list[str],
) -> None:
    """Store curation results on a post."""
    insights_json = json.dumps(key_insights)
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            UPDATE posts
            SET curation_score = ?, summary = ?, key_insights = ?
            WHERE id = ?
            """,
            (curation_score, summary, insights_json, post_id),
        )
        await db.commit()


async def create_digest(
    run_id: int,
    week_label: str,
    post_ids: list[int],
) -> None:
    """Create a digest record linking curated post ids to a run/week."""
    generated_at = datetime.utcnow().isoformat()
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            INSERT INTO digests (run_id, week_label, generated_at, post_ids)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, week_label, generated_at, json.dumps(post_ids)),
        )
        await db.commit()


async def mark_post_curated(post_id: int) -> None:
    """Set is_curated = 1 on a post."""
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            "UPDATE posts SET is_curated = 1 WHERE id = ?",
            (post_id,),
        )
        await db.commit()
