/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Inter'", "'Public Sans'", "system-ui", "-apple-system", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        ink: {
          50: "#FAFAFC",
          100: "#F1F5F9",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#94A3B8",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#111827",
          950: "#0B0F17",
        },
        pink: {
          50: "#FFF1F7",
          100: "#FCE7F3",
          200: "#FBCFE8",
          300: "#F9A8D4",
          400: "#F472B6",
          500: "#EC4899",
          600: "#DB2777",
          700: "#BE185D",
          800: "#9D174D",
          900: "#831843",
          950: "#500724",
        },
        brand: {
          50: "#FFF1F7",
          100: "#FCE7F3",
          200: "#FBCFE8",
          300: "#F9A8D4",
          400: "#F472B6",
          500: "#EC4899",
          600: "#DB2777",
          700: "#BE185D",
          800: "#9D174D",
          900: "#831843",
          950: "#500724",
        },
        emergency: "#E11D48",
        urgent: "#EA580C",
        standard: "#10B981",
        undetermined: "#64748B",
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.03), 0 1px 2px -1px rgba(0, 0, 0, 0.03)",
        soft: "0 4px 20px -2px rgba(236, 72, 153, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.04)",
        glow: "0 0 24px 0 rgba(236, 72, 153, 0.35)",
        panel: "0 1px 3px rgba(0, 0, 0, 0.04)",
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
