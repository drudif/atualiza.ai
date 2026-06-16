import Link from "next/link";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { posts } from "@/lib/schema";
import { eq } from "drizzle-orm";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PostPage({ params }: PageProps) {
  const { id } = await params;
  const postId = parseInt(id, 10);
  if (isNaN(postId)) notFound();

  const results = await db.select().from(posts).where(eq(posts.id, postId)).limit(1);
  const post = results[0];
  if (!post) notFound();

  let topicIds: string[] = [];
  let topComments: Array<{ author: string; score: number; body: string }> = [];
  let keyInsights: string[] = [];

  try { topicIds = JSON.parse(post.topicIds); } catch {}
  try { topComments = JSON.parse(post.topComments ?? "[]"); } catch {}
  try { keyInsights = JSON.parse(post.keyInsights ?? "[]"); } catch {}

  return (
    <main className="min-h-screen bg-paper">
      {/* ── Header strip ── */}
      <div className="border-b-2 border-ink bg-paper sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="font-satoshi font-bold text-xs uppercase tracking-widest text-muted hover:text-ink transition-colors"
          >
            ← Feed
          </Link>
          <span className="font-satoshi font-black text-sm uppercase tracking-tight text-ink">
            Creative AI News Feed
          </span>
        </div>
      </div>

      <article className="max-w-3xl mx-auto px-6 py-10">
        {/* ── Meta strip ── */}
        <div className="flex flex-wrap items-center gap-0 border-2 border-ink mb-6 shadow-brutal-sm">
          <span className="font-satoshi text-xs font-bold uppercase tracking-widest px-4 py-2.5 border-r-2 border-ink text-muted bg-surface">
            r/{post.subreddit}
          </span>
          <span className="font-courier text-xs px-4 py-2.5 border-r-2 border-ink text-muted">
            ↑ {post.score.toLocaleString()}
          </span>
          {post.curationScore && (
            <span className="font-satoshi text-xs font-black px-4 py-2.5 border-r-2 border-ink bg-accent text-yellow">
              {post.curationScore}/10
            </span>
          )}
          <div className="flex gap-0 flex-wrap ml-auto">
            {topicIds.map((t, i) => (
              <span
                key={t}
                className={[
                  "font-satoshi text-xs font-medium uppercase tracking-wide px-3 py-2.5 text-muted",
                  i > 0 ? "border-l-2 border-ink" : "",
                ].join(" ")}
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* ── Title ── */}
        <h1 className="font-satoshi font-black text-3xl md:text-4xl leading-tight text-ink mb-6">
          {post.title}
        </h1>

        {/* ── Reddit link ── */}
        <a
          href={post.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 font-satoshi text-xs font-bold uppercase tracking-widest border-2 border-ink px-5 py-2.5 bg-ink text-cream hover:bg-muted transition-colors shadow-brutal-sm mb-10"
        >
          Ver no Reddit ↗
        </a>

        {/* ── Summary ── */}
        {post.summary && (
          <section className="border-2 border-ink mb-6 shadow-brutal">
            <div className="border-b-2 border-ink px-5 py-2 bg-surface">
              <h2 className="font-satoshi text-xs font-bold uppercase tracking-[0.2em] text-muted">
                Resumo
              </h2>
            </div>
            <div className="px-6 py-5 bg-cream">
              <p className="font-courier text-base leading-[1.8] text-ink">
                {post.summary}
              </p>
            </div>
          </section>
        )}

        {/* ── Key insights ── */}
        {keyInsights.length > 0 && (
          <section className="border-2 border-ink mb-6 shadow-brutal">
            <div className="border-b-2 border-ink px-5 py-2 bg-accent">
              <h2 className="font-satoshi text-xs font-bold uppercase tracking-[0.2em] text-yellow">
                Insights dos comentários
              </h2>
            </div>
            <div className="bg-cream">
              {keyInsights.map((insight, i) => (
                <div
                  key={i}
                  className={[
                    "flex gap-4 px-6 py-4 font-courier text-sm leading-[1.75] text-ink",
                    i < keyInsights.length - 1 ? "border-b-2 border-ink" : "",
                  ].join(" ")}
                >
                  <span className="font-satoshi font-black text-yellow bg-accent px-1 shrink-0 mt-0.5">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{insight}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Top comments ── */}
        {topComments.length > 0 && (
          <section className="border-2 border-ink shadow-brutal">
            <div className="border-b-2 border-ink px-5 py-2 bg-surface">
              <h2 className="font-satoshi text-xs font-bold uppercase tracking-[0.2em] text-muted">
                Comentários em destaque
              </h2>
            </div>
            <div className="bg-cream">
              {topComments.map((comment, i) => (
                <div
                  key={i}
                  className={[
                    "px-6 py-5",
                    i < topComments.length - 1 ? "border-b-2 border-ink" : "",
                  ].join(" ")}
                >
                  <div className="flex items-center gap-4 mb-3">
                    <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-ink">
                      u/{comment.author}
                    </span>
                    <span className="font-courier text-xs text-muted">
                      ↑ {comment.score}
                    </span>
                  </div>
                  <p className="font-courier text-sm leading-[1.75] text-ink/80">
                    {comment.body}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Back link ── */}
        <div className="mt-10 pt-6 border-t-2 border-ink">
          <Link
            href="/"
            className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted hover:text-ink transition-colors"
          >
            ← Voltar ao feed
          </Link>
        </div>
      </article>
    </main>
  );
}
