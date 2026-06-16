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
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-3 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <Link
          href={`/post/${id}`}
          className="text-white font-medium leading-snug hover:text-blue-400 transition-colors line-clamp-3"
        >
          {title}
        </Link>
        {curationScore !== null && (
          <span
            className={cn(
              "shrink-0 text-xs font-bold px-2 py-1 rounded-full",
              curationScore >= 8
                ? "bg-green-900 text-green-300"
                : curationScore >= 6
                ? "bg-yellow-900 text-yellow-300"
                : "bg-gray-800 text-gray-400"
            )}
          >
            {curationScore}/10
          </span>
        )}
      </div>

      {summary && (
        <p className="text-gray-400 text-sm leading-relaxed line-clamp-3">
          {summary}
        </p>
      )}

      <div className="flex items-center gap-3 text-xs text-gray-500 mt-auto pt-2 border-t border-gray-800">
        <span className="font-medium text-gray-400">r/{subreddit}</span>
        <span>↑ {score.toLocaleString()}</span>
        <div className="flex gap-1 ml-auto flex-wrap justify-end">
          {topicIds.slice(0, 2).map((t) => (
            <span key={t} className="bg-gray-800 px-2 py-0.5 rounded text-gray-400">
              {t}
            </span>
          ))}
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:text-blue-400 ml-1"
        >
          ↗
        </a>
      </div>
    </div>
  );
}
