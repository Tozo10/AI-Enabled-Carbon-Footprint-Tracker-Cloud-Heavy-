export default {
  plugins: {
    '@tailwindcss/postcss': {}, // <--- THIS IS THE FIX
    autoprefixer: {},
  },
}