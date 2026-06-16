import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as schema from "./schema";
import path from "path";
import fs from "fs";

const dbPath = process.env.DB_PATH ?? path.join(process.cwd(), "../db/feed.db");

// Ensure parent directory exists
fs.mkdirSync(path.dirname(dbPath), { recursive: true });

const sqlite = new Database(dbPath);

// Initialize tables on first run
sqlite.exec(`
  CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    posts_scraped INTEGER DEFAULT 0,
    posts_curated INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
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

  CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    week_label TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    post_ids TEXT NOT NULL
  );
`);

export const db = drizzle(sqlite, { schema });
