import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          red: "#EF2D2D",
          "red-alt": "#EF2F32",
          "red-dark": "#D62828",
          orange: "#F59E0B",
          "orange-alt": "#F4A51C",
          "orange-light": "#FFD37A",
        },
        bg: {
          page: "#F7F8FA",
          main: "#F8F8F8",
        },
        border: {
          DEFAULT: "#E5E7EB",
          secondary: "#ECECEC",
          divider: "#DADADA",
        },
        text: {
          primary: "#1F2937",
          heading: "#111827",
          secondary: "#6B7280",
          placeholder: "#9CA3AF",
          disabled: "#C4C4C4",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "sans-serif"],
      },
      borderRadius: {
        card: "18px",
        bubble: "18px",
        btn: "14px",
        pill: "999px",
        input: "28px",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
