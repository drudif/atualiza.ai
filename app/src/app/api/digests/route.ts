import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { digests, runs } from "@/lib/schema";
import { desc } from "drizzle-orm";

export async function GET() {
  try {
    const results = await db
      .select()
      .from(digests)
      .orderBy(desc(digests.generatedAt))
      .limit(20);
    return NextResponse.json({ digests: results });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
