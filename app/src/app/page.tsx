import { Suspense } from "react";
import { db } from "@/lib/db";
import { posts, digests } from "@/lib/schema";
import { eq, desc } from "drizzle-orm";
import { PostCard } from "@/components/PostCard";
import { TopicFilter } from "@/components/TopicFilter";
import { RunButton } from "@/components/RunButton";

interface PageProps {
  searchParams: Promise<{ topic?: string; week?: string }>;
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const activeTopic = params.topic ?? null;

  // Fetch curated posts
  let allPosts = await db
    .select()
    .from(posts)
    .where(eq(posts.isCurated, 1))
    .orderBy(desc(posts.curationScore));

  // Filter by topic
  if (activeTopic) {
    allPosts = allPosts.filter((p) => {
      try {
        const topics: string[] = JSON.parse(p.topicIds);
        return topics.includes(activeTopic);
      } catch {
        return false;
      }
    });
  }

  // Latest digest info
  const latestDigests = await db
    .select()
    .from(digests)
    .orderBy(desc(digests.generatedAt))
    .limit(5);

  const latestDigest = latestDigests[0];

  return (
    <main className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white">Creative AI Feed</h1>
            {latestDigest && (
              <p className="text-xs text-gray-500 mt-0.5">
                Semana {latestDigest.weekLabel} · {allPosts.length} posts selecionados
              </p>
            )}
          </div>
          <RunButton />
        </div>
      </header>

      {/* Digest history pills */}
      {latestDigests.length > 1 && (
        <div className="border-b border-gray-800 bg-gray-950">
          <div className="container mx-auto px-4 py-2 flex gap-2 overflow-x-auto">
            {latestDigests.map((d) => (
              <a
                key={d.id}
                href={`/?week=${d.weekLabel}`}
                className="shrink-0 text-xs px-3 py-1 rounded-full bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors"
              >
                {d.weekLabel}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Topic filter */}
      <div className="container mx-auto px-4 py-4">
        <Suspense>
          <TopicFilter activeTopic={activeTopic} />
        </Suspense>
      </div>

      {/* Feed grid */}
      <div className="container mx-auto px-4 pb-12">
        {allPosts.length === 0 ? (
          <div className="text-center py-24 text-gray-600">
            <p className="text-lg">Nenhum post ainda.</p>
            <p className="text-sm mt-2">Clique em "Rodar agora" para buscar os posts da semana.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
            {allPosts.map((post) => {
              let topicIds: string[] = [];
              try { topicIds = JSON.parse(post.topicIds); } catch {}
              return (
                <PostCard
                  key={post.id}
                  id={post.id}
                  title={post.title}
                  subreddit={post.subreddit}
                  score={post.score}
                  curationScore={post.curationScore}
                  summary={post.summary}
                  topicIds={topicIds}
                  url={post.url}
                />
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
