export const TOPICS = [
  { id: "nano-banana", label: "Nano Banana" },
  { id: "omni-flash", label: "Gemini Omni Flash" },
  { id: "midjourney", label: "Midjourney" },
  { id: "seedance", label: "Seedance" },
  { id: "kling", label: "Kling" },
  { id: "image-gen", label: "Image Generation" },
  { id: "video-gen", label: "Video Generation" },
  { id: "vibe-design", label: "Vibecoding Design" },
  { id: "vibe-automation", label: "Vibecoding Automação" },
  { id: "general", label: "GenAI Geral" },
] as const;

export type TopicId = (typeof TOPICS)[number]["id"];
