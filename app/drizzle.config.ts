import type { Config } from "drizzle-kit";
import path from "path";

const tursoUrl = process.env.TURSO_DATABASE_URL;
const url = tursoUrl ?? `file:${process.env.DB_PATH ?? path.join(__dirname, "../db/feed.db")}`;

export default {
  schema: "./src/lib/schema.ts",
  out: "./drizzle",
  dialect: "turso",
  dbCredentials: tursoUrl
    ? { url: tursoUrl, authToken: process.env.TURSO_AUTH_TOKEN }
    : { url },
} satisfies Config;
