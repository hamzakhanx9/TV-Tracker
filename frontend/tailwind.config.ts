import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        frame: {
          bg: "#09090B",
          surface: "#18181B",
          elevated: "#27272A",
          accent: "#8B83F6",
        },
      },
    },
  },
  plugins: [],
};

export default config;
