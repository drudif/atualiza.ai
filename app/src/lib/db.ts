import { drizzle } from "drizzle-orm/libsql";
import { createClient } from "@libsql/client";
import * as schema from "./schema";
import path from "path";
import fs from "fs";

// Env-driven: com TURSO_DATABASE_URL conecta no Turso (libsql remoto);
// sem ele, usa um arquivo SQLite local (file:) — dev continua igual.
// As tabelas são criadas pelo scraper (store.init_db).
let url: string;
const authToken = process.env.TURSO_AUTH_TOKEN;

if (process.env.TURSO_DATABASE_URL) {
  url = process.env.TURSO_DATABASE_URL;
} else {
  const dbPath = process.env.DB_PATH ?? path.join(process.cwd(), "../db/feed.db");
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  url = `file:${dbPath}`;
}

const client = createClient({ url, authToken });

export const db = drizzle(client, { schema });
