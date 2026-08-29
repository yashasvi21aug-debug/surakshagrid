/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        suraksha: {
          bg: "#0B0F19",
          card: "#111827",
          border: "#1F2937",
          danger: "#EF4444",
          warning: "#F59E0B",
          success: "#10B981",
          primary: "#3B82F6",
          accent: "#06B6D4",
        },
      },
    },
  },
  plugins: [],
};
