import { Suspense } from "react";
import { db } from "@/lib/db";
import { posts, digests } from "@/lib/schema";
import { desc, inArray } from "drizzle-orm";
import { Headliner } from "@/components/Headliner";
import { SubStory } from "@/components/SubStory";
import { FeedItem } from "@/components/FeedItem";
import { TopicFilter } from "@/components/TopicFilter";
import { ScraperMonitor } from "@/components/ScraperMonitor";
import { getGroupTopicIds } from "@/lib/topics";

type Post = typeof posts.$inferSelect;

interface PageProps {
  searchParams: Promise<{ topic?: string; week?: string }>;
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const activeTopic = params.topic ?? null;
  const activeWeek = params.week ?? null;

  const allDigests = await db
    .select()
    .from(digests)
    .orderBy(desc(digests.generatedAt))
    .limit(10);

  // Unique weeks for navigation (latest digest per week)
  const seenWeeks = new Set<string>();
  const uniqueWeeks = allDigests.filter((d) => {
    if (seenWeeks.has(d.weekLabel)) return false;
    seenWeeks.add(d.weekLabel);
    return true;
  });

  const selectedWeek = activeWeek ?? uniqueWeeks[0]?.weekLabel ?? null;

  // Collect ALL digests for the selected week and union their postIds
  const weekDigests = allDigests.filter((d) => d.weekLabel === selectedWeek);
  const allPostIds = [
    ...new Set(
      weekDigests.flatMap((d) => {
        try { return JSON.parse(d.postIds) as number[]; } catch { return []; }
      })
    ),
  ];

  let feedPosts: Post[] = [];
  if (allPostIds.length > 0) {
    feedPosts = (await db
      .select()
      .from(posts)
      .where(inArray(posts.id, allPostIds))
      .orderBy(desc(posts.curationScore))) as Post[];
  }

  if (activeTopic) {
    const filterIds = getGroupTopicIds(activeTopic);
    feedPosts = feedPosts.filter((p) => {
      try {
        const topics: string[] = JSON.parse(p.topicIds);
        return filterIds.some((id) => topics.includes(id));
      } catch { return false; }
    });
  }

  const parseTopics = (p: Post) => {
    try { return JSON.parse(p.topicIds) as string[]; } catch { return []; }
  };
  const parseInsights = (p: Post) => {
    try { return JSON.parse(p.keyInsights ?? "[]") as string[]; } catch { return []; }
  };

  const headliner = feedPosts[0] ?? null;
  const subStories = feedPosts.slice(1, 3);
  const restPosts = feedPosts.slice(3);

  return (
    <main className="min-h-screen bg-paper">
      {/* ── Header ── */}
      <header className="sticky top-0 z-20 bg-paper border-b-2 border-ink">
        <div className="max-w-feed mx-auto px-6 py-4 flex items-center justify-between gap-6">
          <div className="flex items-baseline gap-5 min-w-0">
            <h1 className="font-satoshi font-black text-xl md:text-2xl uppercase tracking-tight text-ink whitespace-nowrap">
              Creative AI News Feed{" "}
              <span className="font-normal normal-case tracking-normal text-base text-muted">by convert</span>
            </h1>
            {selectedWeek && (
              <span className="font-courier text-xs text-muted hidden sm:inline truncate">
                {selectedWeek} &mdash; {feedPosts.length} posts curados
              </span>
            )}
          </div>
          <ScraperMonitor />
        </div>
      </header>

      {/* ── Week navigation ── */}
      {uniqueWeeks.length > 0 && (
        <div className="border-b-2 border-ink bg-surface overflow-x-auto">
          <div className="max-w-feed mx-auto px-6 flex">
            {uniqueWeeks.map((d, i) => {
              const isActive = selectedWeek === d.weekLabel;
              const runCount = allDigests.filter((x) => x.weekLabel === d.weekLabel).length;
              return (
                <a
                  key={d.weekLabel}
                  href={`/?week=${d.weekLabel}`}
                  className={[
                    "shrink-0 font-courier text-xs py-2.5 px-4 transition-colors",
                    i < uniqueWeeks.length - 1 ? "border-r-2 border-ink" : "",
                    isActive
                      ? "bg-accent text-yellow font-bold"
                      : "text-muted hover:text-ink hover:bg-paper",
                  ].join(" ")}
                >
                  {d.weekLabel}
                  {runCount > 1 && (
                    <span className="ml-1.5 opacity-60">×{runCount}</span>
                  )}
                </a>
              );
            })}
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

      {/* ── Feed ── */}
      <div className="max-w-feed mx-auto px-6 py-10">
        {feedPosts.length === 0 ? (
          <div className="border-2 border-ink p-16 text-center bg-cream shadow-brutal">
            <p className="font-satoshi font-black text-2xl text-ink mb-3">Feed vazio.</p>
            <p className="font-courier text-sm text-muted leading-relaxed">
              Clique em &ldquo;rodar agora&rdquo; para buscar os destaques da semana.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-0">

            {/* Headliner */}
            {headliner && (
              <Headliner
                id={headliner.id}
                title={headliner.title}
                subreddit={headliner.subreddit}
                score={headliner.score}
                curationScore={headliner.curationScore}
                summary={headliner.summary}
                keyInsights={parseInsights(headliner)}
                topicIds={parseTopics(headliner)}
                url={headliner.url}
              />
            )}

            {/* Sub-stories */}
            {subStories.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 border-l-2 border-r-2 border-b-2 border-ink">
                {subStories.map((post, i) => (
                  <div
                    key={post.id}
                    className={i === 0 && subStories.length > 1 ? "md:border-r-2 border-ink" : ""}
                  >
                    <SubStory
                      id={post.id}
                      title={post.title}
                      subreddit={post.subreddit}
                      score={post.score}
                      curationScore={post.curationScore}
                      summary={post.summary}
                      topicIds={parseTopics(post)}
                      url={post.url}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* Rest of feed */}
            {restPosts.length > 0 && (
              <div className="border-2 border-t-0 border-ink bg-cream">
                <div className="border-b-2 border-ink px-6 py-3 bg-surface flex items-center gap-3">
                  <span className="font-satoshi text-xs font-bold uppercase tracking-[0.2em] text-muted">
                    Mais destaques
                  </span>
                  <span className="font-courier text-xs text-muted/60">
                    {restPosts.length} {restPosts.length === 1 ? "post" : "posts"}
                  </span>
                </div>
                <div className="px-6 divide-y-0">
                  {restPosts.map((post, i) => (
                    <FeedItem
                      key={post.id}
                      index={i + 4}
                      id={post.id}
                      title={post.title}
                      subreddit={post.subreddit}
                      score={post.score}
                      curationScore={post.curationScore}
                      summary={post.summary}
                      topicIds={parseTopics(post)}
                      url={post.url}
                    />
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <footer className="border-t-2 border-ink mt-4 bg-surface">
        <div className="max-w-feed mx-auto px-6 py-4 flex items-center justify-between">
          <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted">
            Creative AI News Feed · convert
          </span>
          <span className="font-courier text-xs text-muted">
            Scrape semanal · r/IA criativa
          </span>
        </div>
      </footer>
    </main>
  );
}
