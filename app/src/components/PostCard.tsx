import Link from "next/link";
import { cn } from "@/lib/utils";

interface PostCardProps {
  id: number;
  title: string;
  subreddit: string;
  score: number;
  curationScore: number | null;
  summary: string | null;
  topicIds: string[];
  url: string;
}

export function PostCard({
  id,
  title,
  subreddit,
  score,
  curationScore,
  summary,
  topicIds,
  url,
}: PostCardProps) {
  const isTop = curationScore !== null && curationScore >= 8;

  return (
    <article
      className={cn(
        "border-2 border-ink bg-cream flex flex-col",
        "shadow-brutal transition-all duration-100",
        "hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-lg"
      )}
    >
      {/* Score strip */}
      {curationScore !== null && (
        <div
          className={cn(
            "border-b-2 border-ink px-4 py-2 flex items-center justify-between",
            isTop ? "bg-ink" : "bg-surface"
          )}
        >
          <span
            className={cn(
              "font-satoshi text-xs font-bold uppercase tracking-[0.2em]",
              isTop ? "text-cream" : "text-muted"
            )}
          >
            Curadoria
          </span>
          <span
            className={cn(
              "font-satoshi text-sm font-black",
              isTop ? "text-cream" : "text-ink"
            )}
          >
            {curationScore}
            <span className={cn("font-normal text-xs", isTop ? "text-cream/60" : "text-muted")}>
              /10
            </span>
          </span>
        </div>
      )}

      {/* Body */}
      <div className="p-5 flex flex-col gap-3 flex-1">
        <Link
          href={`/post/${id}`}
          className="font-satoshi font-bold text-lg leading-tight text-ink hover:text-accent transition-colors"
        >
          {title}
        </Link>

        {summary && (
          <p className="font-courier text-sm leading-[1.7] text-ink/75 line-clamp-4">
            {summary}
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="border-t-2 border-ink px-5 py-3 flex items-center gap-3 bg-surface flex-wrap">
        <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted">
          r/{subreddit}
        </span>
        <span className="font-courier text-xs text-muted">↑ {score.toLocaleString()}</span>

        <div className="flex gap-1.5 ml-auto flex-wrap justify-end">
          {topicIds.slice(0, 2).map((t) => (
            <span
              key={t}
              className="border border-ink text-xs px-2 py-0.5 font-satoshi font-medium uppercase tracking-wide text-muted"
            >
              {t}
            </span>
          ))}
        </div>

        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Ver original no Reddit"
          className="font-satoshi text-sm font-bold text-ink hover:text-accent transition-colors shrink-0"
        >
          ↗
        </a>
      </div>
    </article>
  );
}
