/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: "var(--bg)",
        cardBg: "var(--surface)",
        sidebarBg: "var(--sidebar-bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        accentPurple: "var(--accent)",
        accentBlue: "var(--accent-2)",
        accentMagenta: "var(--pastel-peach)",
        accentTeal: "var(--pastel-cyan)",
        accentGreen: "var(--success)",
        accentOrange: "var(--warning)",
        
        // Border and text styling tokens
        border: "var(--border)",
        textPrimary: "var(--text)",
        textSecondary: "var(--text-muted)",
        textMuted: "var(--text-dim)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      }
    },
  },
  plugins: [],
}
