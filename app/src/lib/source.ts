const SOURCE_LABELS: Record<string, string> = {
  hackernews: "HN",
  arxiv: "arXiv",
  lobsters: "Lobsters",
  devto: "Dev.to",
  itsnicethat: "It's Nice That",
  kdnuggets: "KDnuggets",
  medium: "Medium",
  openai: "OpenAI",
  googleresearch: "Google Research",
  actuia: "ActuIA",
  adobe: "Adobe Blog",
  runway: "Runway",
};

export function formatSource(subreddit: string): string {
  return SOURCE_LABELS[subreddit] ?? `r/${subreddit}`;
}
