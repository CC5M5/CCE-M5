/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        liturgia: {
          verde: '#1e5631',
          'verde-claro': '#2d7a4a',
          morado: '#4a148c',
          'morado-claro': '#6a1b9a',
          rosa: '#c2185b',
          'rosa-claro': '#e91e63',
          rojo: '#b71c1c',
          'rojo-claro': '#d32f2f',
          blanco: '#f5f5f5',
          dorado: '#ffb300',
        },
      },
      fontFamily: {
        heading: ['Montserrat', 'sans-serif'],
        body: ['Merriweather', 'serif'],
        sans: ['Montserrat', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
