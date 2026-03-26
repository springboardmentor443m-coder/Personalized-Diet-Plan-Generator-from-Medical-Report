/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        lavender: {
          light: "#E6E6FA",
          DEFAULT: "#C8A2C8",
          dark: "#9F7AEA",
        },
      },
    },
  },
  plugins: [],
};