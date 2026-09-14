/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Noto Sans Thai"', '"Inter"', 'sans-serif'],
      },
      colors: {
        indigo: {
          50: '#F6F5FF',
          100: '#EEF0FF',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312A6B',
        },
        ink: {
          DEFAULT: '#171733', // headings / titles — high contrast
          soft: '#3F3F57', // body text
          faint: '#62627A', // secondary text (location, captions) — still readable
        },
        line: '#E6E3F4',
        pagebg: '#F5F4FB',
        amber: {
          bg: '#FFF6E4',
          line: '#F3DFAE',
          ink: '#8A5A00',
          icon: '#D98E04',
        },
        gold: '#F5A623',
      },
      boxShadow: {
        card: '0 1px 2px rgba(33,29,58,0.04), 0 8px 24px -12px rgba(33,29,58,0.12)',
      },
    },
  },
  plugins: [],
}
