import { drizzle } from "drizzle-orm/libsql";
import { createClient } from "@libsql/client";
import * as schema from "./schema";
import path from "path";
import fs from "fs";

// Leitura via libsql (file:). Ordem de resolução do caminho:
//  1. DB_PATH (override explícito — usado no dev local p/ apontar ../db/feed.db)
//  2. data/feed.db embutido no deploy (gerado por `pnpm bundle-db` antes do push)
//  3. ../db/feed.db (monorepo local)
// TURSO_DATABASE_URL ainda é suportado, caso um dia se queira um banco hospedado.
let url: string;
const authToken = process.env.TURSO_AUTH_TOKEN;

if (process.env.TURSO_DATABASE_URL) {
  url = process.env.TURSO_DATABASE_URL;
} else {
  const bundled = path.join(process.cwd(), "data", "feed.db");
  const sibling = path.join(process.cwd(), "../db/feed.db");
  const dbPath =
    process.env.DB_PATH ?? (fs.existsSync(bundled) ? bundled : sibling);
  try {
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  } catch {
    // sem permissão de escrita no destino (ex: deploy read-only) — ok, só leitura
  }
  url = `file:${dbPath}`;
}

const client = createClient({ url, authToken });

export const db = drizzle(client, { schema });
