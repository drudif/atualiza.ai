import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        satoshi: ["Satoshi", "system-ui", "sans-serif"],
        courier: ["'Courier Prime'", "'Courier New'", "monospace"],
      },
      colors: {
        ink: "#1C1917",
        paper: "#EDE8E1",
        surface: "#DDD7CE",
        muted: "#6B5E52",
        accent: "#C0392B",
        cream: "#FAFAF8",
      },
      boxShadow: {
        brutal: "4px 4px 0px #1C1917",
        "brutal-sm": "2px 2px 0px #1C1917",
        "brutal-lg": "6px 6px 0px #1C1917",
        "brutal-accent": "4px 4px 0px #C0392B",
      },
      maxWidth: {
        feed: "1400px",
      },
    },
  },
  plugins: [],
};
export default config;
