import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";

export const runs = sqliteTable("runs", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  startedAt: text("started_at").notNull(),
  finishedAt: text("finished_at"),
  status: text("status").notNull().default("running"),
  postsScraped: integer("posts_scraped").default(0),
  postsCurated: integer("posts_curated").default(0),
});

export const posts = sqliteTable("posts", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  runId: integer("run_id").notNull(),
  subreddit: text("subreddit").notNull(),
  topicIds: text("topic_ids").notNull(),   // JSON string
  title: text("title").notNull(),
  url: text("url").notNull().unique(),
  score: integer("score").notNull(),
  numComments: integer("num_comments").notNull(),
  author: text("author"),
  createdUtc: text("created_utc"),
  bodyMd: text("body_md"),
  topComments: text("top_comments"),       // JSON string
  isCurated: integer("is_curated").default(0),
  curationScore: integer("curation_score"),
  summary: text("summary"),
  keyInsights: text("key_insights"),       // JSON string
});

export const digests = sqliteTable("digests", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  runId: integer("run_id").notNull(),
  weekLabel: text("week_label").notNull(),
  generatedAt: text("generated_at").notNull(),
  postIds: text("post_ids").notNull(),     // JSON string
});
