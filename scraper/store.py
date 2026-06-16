"""Async storage (libsql / Turso) for creative-ai-feed scraper.

Env-driven: com TURSO_DATABASE_URL aponta para o Turso (libsql remoto); sem ele,
usa um arquivo SQLite local (file:) — o fluxo de desenvolvimento continua igual.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import libsql_client

# DB local padrão (usado quando TURSO_DATABASE_URL não está definido)
_DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "db" / "feed.db")

_client = None  # singleton libsql_client.Client

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


def _resolve_url() -> tuple[str, str | None]:
    """Retorna (url, auth_token). Turso se configurado, senão arquivo local."""
    turso = os.getenv("TURSO_DATABASE_URL")
    if turso:
        return turso, os.getenv("TURSO_AUTH_TOKEN")
    path = os.getenv("DB_PATH", _DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return f"file:{path}", None


def _get():
    global _client
    if _client is None:
        url, token = _resolve_url()
        _client = libsql_client.create_client(url, auth_token=token)
    return _client


async def close() -> None:
    """Fecha o client libsql (chamado ao fim do run)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def init_db() -> None:
    """Cria as tabelas se não existirem."""
    client = _get()
    await client.execute(_CREATE_RUNS)
    await client.execute(_CREATE_POSTS)
    await client.execute(_CREATE_DIGESTS)


async def create_run() -> int:
    """Insere um novo run e retorna o id."""
    started_at = datetime.utcnow().isoformat()
    rs = await _get().execute(
        "INSERT INTO runs (started_at, status) VALUES (?, 'running')",
        [started_at],
    )
    return rs.last_insert_rowid


async def finish_run(
    run_id: int,
    status: str,
    posts_scraped: int,
    posts_curated: int,
) -> None:
    """Marca um run como finalizado com as estatísticas finais."""
    finished_at = datetime.utcnow().isoformat()
    await _get().execute(
        """
        UPDATE runs
        SET finished_at = ?, status = ?, posts_scraped = ?, posts_curated = ?
        WHERE id = ?
        """,
        [finished_at, status, posts_scraped, posts_curated, run_id],
    )


async def url_exists(url: str) -> bool:
    """True se já existe um post com esta URL."""
    rs = await _get().execute(
        "SELECT 1 FROM posts WHERE url = ? LIMIT 1", [url]
    )
    return len(rs.rows) > 0


async def save_post(post: dict, run_id: int) -> int:
    """Insere um post e retorna o id."""
    topic_ids = json.dumps(post.get("topic_ids", []))
    top_comments = json.dumps(post.get("top_comments", []))
    rs = await _get().execute(
        """
        INSERT INTO posts (
            run_id, subreddit, topic_ids, title, url, score, num_comments,
            author, created_utc, body_md, top_comments
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
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
        ],
    )
    return rs.last_insert_rowid


async def update_post_curation(
    post_id: int,
    curation_score: int,
    summary: str,
    key_insights: list[str],
) -> None:
    """Grava os resultados da curadoria em um post."""
    await _get().execute(
        """
        UPDATE posts
        SET curation_score = ?, summary = ?, key_insights = ?
        WHERE id = ?
        """,
        [curation_score, summary, json.dumps(key_insights), post_id],
    )


async def create_digest(
    run_id: int,
    week_label: str,
    post_ids: list[int],
) -> None:
    """Cria um digest ligando os post ids curados a um run/semana."""
    generated_at = datetime.utcnow().isoformat()
    await _get().execute(
        """
        INSERT INTO digests (run_id, week_label, generated_at, post_ids)
        VALUES (?, ?, ?, ?)
        """,
        [run_id, week_label, generated_at, json.dumps(post_ids)],
    )


async def mark_post_curated(post_id: int) -> None:
    """Seta is_curated = 1 em um post."""
    await _get().execute(
        "UPDATE posts SET is_curated = 1 WHERE id = ?",
        [post_id],
    )
