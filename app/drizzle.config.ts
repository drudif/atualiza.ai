import type { Config } from "drizzle-kit";
import path from "path";

const dbPath = process.env.DB_PATH ?? path.join(__dirname, "../db/feed.db");

export default {
  schema: "./src/lib/schema.ts",
  out: "./drizzle",
  dialect: "sqlite",
  dbCredentials: { url: dbPath },
} satisfies Config;
