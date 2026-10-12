import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        vault: {
          50: "#f0f4ff",
          100: "#e0eaff",
          200: "#c7d8fe",
          300: "#a4befe",
          400: "#7c9dfb",
          500: "#5d78f6",
          600: "#4457eb",
          700: "#3744d4",
          800: "#2f3ab0",
          900: "#1e245a",
          950: "#0b0d24",
        },
      },
    },
  },
  plugins: [],
};
export default config;
