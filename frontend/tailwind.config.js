export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        graphite: "#1A1C1F",
        surface: "#232629",
        border: "#33373B",
        muted: "#8B9096",
        teal: "#4F9D94",
        amber: "#D9A441",
        danger: "#C96A5A",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};