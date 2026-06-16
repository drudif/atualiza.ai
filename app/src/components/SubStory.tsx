"use client";

import { useState } from "react";
import { formatSource } from "@/lib/source";

interface SubStoryProps {
  id: number;
  title: string;
  subreddit: string;
  score: number;
  curationScore: number | null;
  summary: string | null;
  topicIds: string[];
  url: string;
}

export function SubStory({
  title,
  subreddit,
  score,
  curationScore,
  summary,
  topicIds,
  url,
}: SubStoryProps) {
  const [expanded, setExpanded] = useState(false);
  const isLong = summary != null && summary.length > 200;

  return (
    <article className="border-2 border-ink bg-cream shadow-brutal flex flex-col h-full">
      {/* meta */}
      <div className="border-b-2 border-ink flex items-stretch">
        {curationScore !== null && (
          <div className="border-r-2 border-ink px-3 py-2 bg-accent flex items-center shrink-0">
            <span className="font-satoshi text-xs font-black text-yellow">
              {curationScore}
              <span className="font-normal text-yellow/60">/10</span>
            </span>
          </div>
        )}
        <div className="px-3 py-2 border-r-2 border-ink flex items-center min-w-0">
          <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted truncate">
            {formatSource(subreddit)}
          </span>
        </div>
        <div className="px-3 py-2 flex items-center">
          <span className="font-courier text-xs text-muted">↑ {score.toLocaleString()}</span>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto border-l-2 border-ink px-4 py-2 font-satoshi text-xs font-bold text-ink hover:bg-ink hover:text-cream transition-colors flex items-center shrink-0"
        >
          ↗
        </a>
      </div>

      {/* title */}
      <div className="px-5 pt-5 pb-3 flex-1">
        <h3 className="font-satoshi font-black text-xl md:text-2xl leading-tight text-ink mb-4">
          {title}
        </h3>

        {summary && (
          <>
            <p className={`font-courier text-sm leading-[1.75] text-ink/80 ${!expanded ? "line-clamp-4" : ""}`}>
              {summary}
            </p>
            {isLong && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="mt-2 font-satoshi text-xs font-bold uppercase tracking-[0.15em] text-accent hover:text-ink transition-colors"
              >
                {expanded ? "fechar ↑" : "ler mais ↓"}
              </button>
            )}
          </>
        )}
      </div>

      {/* topics */}
      {topicIds.length > 0 && (
        <div className="border-t-2 border-ink px-5 py-2.5 flex gap-2 flex-wrap bg-surface">
          {topicIds.slice(0, 3).map((t) => (
            <span key={t} className="font-satoshi text-xs uppercase tracking-wide text-muted font-medium">
              {t}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
