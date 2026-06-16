export interface SubTopic {
  id: string;
  label: string;
}

export interface TopicGroup {
  id: string;
  label: string;
  children: SubTopic[];
}

export const TOPIC_GROUPS: TopicGroup[] = [
  {
    id: "image-gen",
    label: "Imagem",
    children: [
      { id: "midjourney", label: "Midjourney" },
      { id: "nano-banana", label: "Nano Banana" },
    ],
  },
  {
    id: "video-gen",
    label: "Vídeo",
    children: [
      { id: "kling", label: "Kling" },
      { id: "seedance", label: "Seedance" },
      { id: "omni-flash", label: "Omni Flash" },
    ],
  },
  { id: "vibe-design",     label: "Design",      children: [] },
  { id: "vibe-automation", label: "Automação",   children: [] },
  { id: "vibe-tools",      label: "Ferramentas", children: [] },
  { id: "general",         label: "GenAI Geral", children: [] },
];

// Flat list for legacy usage (components that show topic badges)
export const TOPICS = TOPIC_GROUPS.flatMap((g) => [
  { id: g.id, label: g.label },
  ...g.children,
]);

export type TopicId = string;

/** All topic IDs that belong to a group (parent + children). */
export function getGroupTopicIds(topicId: string): string[] {
  const group = TOPIC_GROUPS.find((g) => g.id === topicId);
  if (group) return [topicId, ...group.children.map((c) => c.id)];
  return [topicId];
}

/** Find the parent group of a topic (returns itself if it's already a parent). */
export function getParentGroup(topicId: string): TopicGroup | undefined {
  return TOPIC_GROUPS.find(
    (g) => g.id === topicId || g.children.some((c) => c.id === topicId)
  );
}

/** Human-readable label for any topic ID. */
export function getTopicLabel(id: string): string {
  return TOPICS.find((t) => t.id === id)?.label ?? id;
}
