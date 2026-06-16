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
    <main className="min-h-screen bg-gray-950">
      <div className="container mx-auto px-4 py-8 max-w-3xl">
        {/* Back */}
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-6 inline-block">
          ← Voltar ao feed
        </Link>

        {/* Title + meta */}
        <h1 className="text-2xl font-bold text-white leading-snug mt-2">{post.title}</h1>
        <div className="flex items-center gap-3 mt-3 text-sm text-gray-500">
          <span>r/{post.subreddit}</span>
          <span>↑ {post.score.toLocaleString()}</span>
          {post.curationScore && (
            <span className="bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full text-xs font-medium">
              {post.curationScore}/10
            </span>
          )}
          <div className="flex gap-1 ml-auto flex-wrap">
            {topicIds.map((t) => (
              <span key={t} className="bg-gray-800 px-2 py-0.5 rounded text-gray-400 text-xs">
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* Link to original */}
        <a
          href={post.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          Ver no Reddit ↗
        </a>

        {/* Summary */}
        {post.summary && (
          <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Resumo</h2>
            <p className="text-gray-200 leading-relaxed">{post.summary}</p>
          </div>
        )}

        {/* Key insights */}
        {keyInsights.length > 0 && (
          <div className="mt-4 bg-gray-900 border border-gray-800 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Insights dos comentários
            </h2>
            <ul className="space-y-2">
              {keyInsights.map((insight, i) => (
                <li key={i} className="flex gap-2 text-gray-300 text-sm leading-relaxed">
                  <span className="text-blue-500 shrink-0">•</span>
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Top comments */}
        {topComments.length > 0 && (
          <div className="mt-6">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Comentários em destaque
            </h2>
            <div className="space-y-3">
              {topComments.map((comment, i) => (
                <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium text-gray-400">u/{comment.author}</span>
                    <span className="text-xs text-gray-600">↑ {comment.score}</span>
                  </div>
                  <p className="text-gray-300 text-sm leading-relaxed">{comment.body}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
