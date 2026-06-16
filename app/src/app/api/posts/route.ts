import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { posts, digests, runs } from "@/lib/schema";
import { eq, desc, and } from "drizzle-orm";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const topicId = searchParams.get("topic");
  const weekLabel = searchParams.get("week");

  try {
    let query = db
      .select()
      .from(posts)
      .where(eq(posts.isCurated, 1))
      .orderBy(desc(posts.curationScore))
      .$dynamic();

    const results = await query;

    const filtered = topicId
      ? results.filter((p) => {
          try {
            const topics: string[] = JSON.parse(p.topicIds);
            return topics.includes(topicId);
          } catch {
            return false;
          }
        })
      : results;

    return NextResponse.json({ posts: filtered });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
