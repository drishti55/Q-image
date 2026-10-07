/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a1a",
        surface: "#0d1b2a",
        border: "rgba(99, 179, 237, 0.15)",
        primary: "#10b981",
        accent: "#06b6d4",
      }
    },
  },
  plugins: [],
}
