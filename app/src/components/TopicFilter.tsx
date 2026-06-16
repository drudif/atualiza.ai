"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { TOPIC_GROUPS, getParentGroup } from "@/lib/topics";

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

  const activeParent = activeTopic ? getParentGroup(activeTopic) : null;

  return (
    <div className="flex flex-wrap gap-0 border-2 border-ink w-fit max-w-full shadow-brutal-sm">
      {/* Todos */}
      <button
        onClick={() => setTopic(null)}
        className={cn(
          "shrink-0 px-5 py-2.5 text-xs font-satoshi font-bold uppercase tracking-[0.18em]",
          "border-r-2 border-ink transition-colors",
          activeTopic === null
            ? "bg-accent text-yellow"
            : "bg-paper text-muted hover:bg-surface"
        )}
      >
        Todos
      </button>

      {TOPIC_GROUPS.map((group, gi) => {
        const isGroupActive = activeTopic === group.id;
        const hasActiveChild = group.children.some((c) => c.id === activeTopic);
        const isParentHighlighted = isGroupActive || hasActiveChild;
        const isLastGroup = gi === TOPIC_GROUPS.length - 1;

        return (
          <div
            key={group.id}
            className={cn(
              "flex items-stretch",
              !isLastGroup || group.children.length > 0 ? "border-r-2 border-ink" : ""
            )}
          >
            {/* Parent button */}
            <button
              onClick={() => setTopic(group.id)}
              className={cn(
                "shrink-0 px-5 py-2.5 text-xs font-satoshi font-black uppercase tracking-[0.18em]",
                "transition-colors",
                group.children.length > 0 ? "border-r-2 border-ink" : "",
                isGroupActive
                  ? "bg-accent text-yellow"
                  : isParentHighlighted
                  ? "bg-surface text-ink"
                  : "bg-paper text-ink hover:bg-surface"
              )}
            >
              {group.label}
            </button>

            {/* Sub-topic chips */}
            {group.children.map((child, ci) => {
              const isChildActive = activeTopic === child.id;
              const isLastChild = ci === group.children.length - 1;
              return (
                <button
                  key={child.id}
                  onClick={() => setTopic(child.id)}
                  className={cn(
                    "shrink-0 px-3 py-2.5 text-[10px] font-satoshi font-bold uppercase tracking-[0.12em]",
                    "transition-colors",
                    !isLastChild ? "border-r border-ink" : "",
                    isChildActive
                      ? "bg-yellow text-ink"
                      : "bg-paper text-muted/40 hover:bg-surface hover:text-muted"
                  )}
                >
                  {child.label}
                </button>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
