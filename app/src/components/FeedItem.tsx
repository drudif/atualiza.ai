import { formatSource } from "@/lib/source";

interface FeedItemProps {
  index: number;
  id: number;
  title: string;
  subreddit: string;
  score: number;
  curationScore: number | null;
  summary: string | null;
  topicIds: string[];
  url: string;
}

export function FeedItem({
  index,
  title,
  subreddit,
  score,
  curationScore,
  summary,
  topicIds,
  url,
}: FeedItemProps) {
  return (
    <article className="border-b-2 border-ink last:border-b-0 py-5 flex gap-5">
      {/* number */}
      <div className="shrink-0 w-10 pt-0.5">
        <span className="font-satoshi font-black text-lg text-surface select-none">
          {String(index).padStart(2, "0")}
        </span>
      </div>

      {/* content */}
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-2">
          <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted">
            {formatSource(subreddit)}
          </span>
          <span className="font-courier text-xs text-muted">↑ {score.toLocaleString()}</span>
          {topicIds.slice(0, 2).map((t) => (
            <span key={t} className="font-satoshi text-xs uppercase tracking-wide text-muted/70">
              {t}
            </span>
          ))}
        </div>

        <h4 className="font-satoshi font-bold text-lg leading-snug text-ink mb-2">
          {title}
        </h4>

        {summary && (
          <p className="font-courier text-sm leading-[1.7] text-ink/70 line-clamp-2">
            {summary}
          </p>
        )}
      </div>

      {/* right: score + link */}
      <div className="shrink-0 flex flex-col items-end gap-2 pt-0.5">
        {curationScore !== null && (
          <span className="font-satoshi text-xs font-black bg-accent text-yellow px-2 py-0.5">
            {curationScore}/10
          </span>
        )}
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-satoshi text-sm font-bold text-muted hover:text-accent transition-colors"
        >
          ↗
        </a>
      </div>
    </article>
  );
}
