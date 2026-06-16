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

  let allPosts = await db
    .select()
    .from(posts)
    .where(eq(posts.isCurated, 1))
    .orderBy(desc(posts.curationScore));

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

  const latestDigests = await db
    .select()
    .from(digests)
    .orderBy(desc(digests.generatedAt))
    .limit(6);

  const latestDigest = latestDigests[0];

  return (
    <main className="min-h-screen bg-paper">
      {/* ── Header ── */}
      <header className="sticky top-0 z-20 bg-paper border-b-2 border-ink">
        <div className="max-w-feed mx-auto px-6 py-4 flex items-center justify-between gap-6">
          <div className="flex items-baseline gap-5 min-w-0">
            <h1 className="font-satoshi font-black text-xl md:text-2xl uppercase tracking-tight text-ink whitespace-nowrap">
              Creative AI Feed
            </h1>
            {latestDigest && (
              <span className="font-courier text-xs text-muted hidden sm:inline truncate">
                {latestDigest.weekLabel} &mdash; {allPosts.length} posts curados
              </span>
            )}
          </div>
          <RunButton />
        </div>
      </header>

      {/* ── Digest history ── */}
      {latestDigests.length > 1 && (
        <div className="border-b-2 border-ink bg-surface overflow-x-auto">
          <div className="max-w-feed mx-auto px-6 flex">
            {latestDigests.map((d, i) => (
              <a
                key={d.id}
                href={`/?week=${d.weekLabel}`}
                className={[
                  "shrink-0 font-courier text-xs py-2.5 px-4 text-muted hover:text-ink hover:bg-paper transition-colors",
                  i < latestDigests.length - 1 ? "border-r-2 border-ink" : "",
                ].join(" ")}
              >
                {d.weekLabel}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* ── Topic filter ── */}
      <div className="border-b-2 border-ink bg-paper">
        <div className="max-w-feed mx-auto px-6 py-4 overflow-x-auto">
          <Suspense>
            <TopicFilter activeTopic={activeTopic} />
          </Suspense>
        </div>
      </div>

      {/* ── Feed grid ── */}
      <div className="max-w-feed mx-auto px-6 py-8">
        {allPosts.length === 0 ? (
          <div className="border-2 border-ink p-16 text-center bg-cream shadow-brutal">
            <p className="font-satoshi font-black text-2xl text-ink mb-3">
              Feed vazio.
            </p>
            <p className="font-courier text-sm text-muted leading-relaxed">
              Clique em &ldquo;rodar agora&rdquo; para buscar os destaques da semana.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {allPosts.map((post) => {
              let topicIds: string[] = [];
              try {
                topicIds = JSON.parse(post.topicIds);
              } catch {}
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

      {/* ── Footer ── */}
      <footer className="border-t-2 border-ink mt-4 bg-surface">
        <div className="max-w-feed mx-auto px-6 py-4 flex items-center justify-between">
          <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted">
            Creative AI Feed
          </span>
          <span className="font-courier text-xs text-muted">
            Scrape semanal · r/IA criativa
          </span>
        </div>
      </footer>
    </main>
  );
}
