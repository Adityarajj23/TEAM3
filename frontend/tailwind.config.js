/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        accent: { DEFAULT: "#1f4fbf", hover: "#183f9a", soft: "#e8eefb", ring: "#7c9be0" },
        ink: "#16202e",
      },
      fontSize: { "2xs": ["0.6875rem", "1rem"] },
    },
  },
  plugins: [],
};
