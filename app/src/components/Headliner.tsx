"use client";

import { useState } from "react";
import { formatSource } from "@/lib/source";

interface HeadlinerProps {
  id: number;
  title: string;
  subreddit: string;
  score: number;
  curationScore: number | null;
  summary: string | null;
  keyInsights: string[];
  topicIds: string[];
  url: string;
}

export function Headliner({
  title,
  subreddit,
  score,
  curationScore,
  summary,
  keyInsights,
  topicIds,
  url,
}: HeadlinerProps) {
  const [insightsOpen, setInsightsOpen] = useState(false);

  return (
    <section className="border-2 border-ink bg-cream shadow-brutal-lg mb-0">
      {/* top meta bar */}
      <div className="border-b-2 border-ink flex items-stretch flex-wrap">
        {curationScore !== null && (
          <div className="border-r-2 border-ink px-4 py-2 bg-accent flex items-center gap-2 shrink-0">
            <span className="font-satoshi text-xs font-bold uppercase tracking-[0.2em] text-yellow">
              manchete
            </span>
            <span className="font-satoshi text-sm font-black text-yellow">
              {curationScore}
              <span className="font-normal text-xs text-yellow/60">/10</span>
            </span>
          </div>
        )}
        <div className="px-4 py-2 border-r-2 border-ink flex items-center">
          <span className="font-satoshi text-xs font-bold uppercase tracking-widest text-muted">
            {formatSource(subreddit)}
          </span>
        </div>
        <div className="px-4 py-2 border-r-2 border-ink flex items-center">
          <span className="font-courier text-xs text-muted">↑ {score.toLocaleString()}</span>
        </div>
        <div className="px-4 py-2 flex items-center gap-2 flex-wrap">
          {topicIds.map((t) => (
            <span key={t} className="font-satoshi text-xs uppercase tracking-wide text-muted font-medium">
              {t}
            </span>
          ))}
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto border-l-2 border-ink px-5 py-2 font-satoshi text-xs font-bold uppercase tracking-[0.18em] bg-ink text-cream hover:bg-accent transition-colors flex items-center shrink-0"
        >
          ver no reddit ↗
        </a>
      </div>

      {/* headline */}
      <div className="px-8 pt-8 pb-6">
        <h2 className="font-satoshi font-black text-3xl md:text-4xl lg:text-5xl leading-[1.05] text-ink">
          {title}
        </h2>
      </div>

      {/* summary */}
      {summary && (
        <div className="border-t-2 border-ink px-8 py-6 bg-paper">
          <p className="font-courier text-base leading-[1.85] text-ink max-w-3xl">
            {summary}
          </p>
        </div>
      )}

      {/* insights */}
      {keyInsights.length > 0 && (
        <div className="border-t-2 border-ink">
          <button
            onClick={() => setInsightsOpen((v) => !v)}
            className="w-full flex items-center justify-between px-8 py-3 bg-surface hover:bg-paper transition-colors text-left"
          >
            <span className="font-satoshi text-xs font-bold uppercase tracking-[0.2em] text-muted">
              {keyInsights.length} insights dos comentários
            </span>
            <span className="font-satoshi text-xs text-muted">{insightsOpen ? "▲" : "▼"}</span>
          </button>
          {insightsOpen && (
            <div className="border-t-2 border-ink divide-y-2 divide-ink">
              {keyInsights.map((insight, i) => (
                <div key={i} className="flex gap-5 px-8 py-4 bg-cream">
                  <span className="font-satoshi font-black text-sm text-yellow bg-accent px-1.5 py-0.5 shrink-0 self-start mt-0.5">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <p className="font-courier text-sm leading-[1.75] text-ink">{insight}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
