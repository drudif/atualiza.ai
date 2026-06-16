"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { TOPICS } from "@/lib/topics";

export function TopicFilter({ activeTopic }: { activeTopic: string | null }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function setTopic(topicId: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (topicId) {
      params.set("topic", topicId);
    } else {
      params.delete("topic");
    }
    router.push(`/?${params.toString()}`);
  }

  return (
    <div className="flex overflow-x-auto border-2 border-ink w-fit max-w-full shadow-brutal-sm">
      <button
        onClick={() => setTopic(null)}
        className={cn(
          "shrink-0 px-5 py-2.5 text-xs font-satoshi font-bold uppercase tracking-[0.18em]",
          "border-r-2 border-ink transition-colors",
          activeTopic === null
            ? "bg-ink text-cream"
            : "bg-paper text-muted hover:bg-surface"
        )}
      >
        Todos
      </button>

      {TOPICS.map((topic, i) => (
        <button
          key={topic.id}
          onClick={() => setTopic(topic.id)}
          className={cn(
            "shrink-0 px-5 py-2.5 text-xs font-satoshi font-bold uppercase tracking-[0.18em]",
            "transition-colors",
            i < TOPICS.length - 1 ? "border-r-2 border-ink" : "",
            activeTopic === topic.id
              ? "bg-ink text-cream"
              : "bg-paper text-muted hover:bg-surface"
          )}
        >
          {topic.label}
        </button>
      ))}
    </div>
  );
}
