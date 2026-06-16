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
        ink: "#04141a",
        paper: "#EDEDEA",
        surface: "#DDD7CE",
        muted: "#6B5E52",
        accent: "#EEE959",
        yellow: "#2A1C71",
        cream: "#FAFAF8",
      },
      boxShadow: {
        brutal: "4px 4px 0px #04141a",
        "brutal-sm": "2px 2px 0px #04141a",
        "brutal-lg": "6px 6px 0px #04141a",
        "brutal-accent": "4px 4px 0px #EEE959",
        "brutal-yellow": "4px 4px 0px #2A1C71",
      },
      maxWidth: {
        feed: "1400px",
      },
    },
  },
  plugins: [],
};
export default config;
