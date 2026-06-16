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
    <div className="flex flex-wrap gap-2">
      <button
        onClick={() => setTopic(null)}
        className={cn(
          "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
          activeTopic === null
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-400 hover:bg-gray-700"
        )}
      >
        Todos
      </button>
      {TOPICS.map((topic) => (
        <button
          key={topic.id}
          onClick={() => setTopic(topic.id)}
          className={cn(
            "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
            activeTopic === topic.id
              ? "bg-blue-600 text-white"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          )}
        >
          {topic.label}
        </button>
      ))}
    </div>
  );
}
