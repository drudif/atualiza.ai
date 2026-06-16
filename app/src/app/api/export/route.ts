import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { posts, digests } from "@/lib/schema";
import { eq, desc, inArray } from "drizzle-orm";
import fs from "fs";
import path from "path";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const weekLabel = searchParams.get("week");

  try {
    // Get the target digest
    let digest;
    if (weekLabel) {
      const results = await db
        .select()
        .from(digests)
        .where(eq(digests.weekLabel, weekLabel))
        .limit(1);
      digest = results[0];
    } else {
      const results = await db
        .select()
        .from(digests)
        .orderBy(desc(digests.generatedAt))
        .limit(1);
      digest = results[0];
    }

    if (!digest) {
      return NextResponse.json({ error: "No digest found" }, { status: 404 });
    }

    const postIds: number[] = JSON.parse(digest.postIds);
    const digestPosts = await db
      .select()
      .from(posts)
      .where(inArray(posts.id, postIds));

    // Parse JSON fields
    const enrichedPosts = digestPosts.map((p) => ({
      ...p,
      topicIds: tryParseJson(p.topicIds, []),
      topComments: tryParseJson(p.topComments, []),
      keyInsights: tryParseJson(p.keyInsights, []),
    }));

    // Build export payload
    const payload = {
      weekLabel: digest.weekLabel,
      generatedAt: digest.generatedAt,
      totalPosts: enrichedPosts.length,
      posts: enrichedPosts,
    };

    // Write JSON file to digests/
    const digestsDir = path.join(process.cwd(), "../digests");
    if (!fs.existsSync(digestsDir)) fs.mkdirSync(digestsDir, { recursive: true });

    const jsonPath = path.join(digestsDir, `${digest.weekLabel}.json`);
    fs.writeFileSync(jsonPath, JSON.stringify(payload, null, 2));

    // Write Markdown file
    const md = buildMarkdown(payload);
    const mdPath = path.join(digestsDir, `${digest.weekLabel}.md`);
    fs.writeFileSync(mdPath, md);

    // Return JSON as download
    return new NextResponse(JSON.stringify(payload, null, 2), {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": `attachment; filename="${digest.weekLabel}.json"`,
      },
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}

function tryParseJson<T>(value: string | null | undefined, fallback: T): T {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function buildMarkdown(payload: {
  weekLabel: string;
  generatedAt: string;
  totalPosts: number;
  posts: Array<{
    title: string;
    url: string;
    subreddit: string;
    score: number;
    curationScore: number | null;
    summary: string | null;
    keyInsights: string[];
    topicIds: string[];
  }>;
}): string {
  const lines: string[] = [
    `# Creative AI Feed — ${payload.weekLabel}`,
    ``,
    `> Gerado em ${payload.generatedAt} • ${payload.totalPosts} posts selecionados`,
    ``,
  ];

  // Group by topic
  const byTopic: Record<string, typeof payload.posts> = {};
  for (const post of payload.posts) {
    const topic = post.topicIds[0] ?? "general";
    if (!byTopic[topic]) byTopic[topic] = [];
    byTopic[topic].push(post);
  }

  for (const [topic, topicPosts] of Object.entries(byTopic)) {
    lines.push(`## ${topic}`);
    lines.push(``);
    for (const post of topicPosts) {
      lines.push(`### [${post.title}](${post.url})`);
      lines.push(`**r/${post.subreddit}** · Score: ${post.score} · Curadoria: ${post.curationScore ?? "?"}/10`);
      lines.push(``);
      if (post.summary) {
        lines.push(post.summary);
        lines.push(``);
      }
      if (post.keyInsights?.length) {
        lines.push(`**Insights dos comentários:**`);
        for (const insight of post.keyInsights) {
          lines.push(`- ${insight}`);
        }
        lines.push(``);
      }
      lines.push(`---`);
      lines.push(``);
    }
  }

  return lines.join("\n");
}
