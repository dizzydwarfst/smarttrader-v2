/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0B0E14',
        surface: '#151A24',
        'surface-hover': '#1E2532',
        border: '#2A3548',
        'border-strong': '#3B4A63',
        'text-primary': '#F8FAFC',
        'text-secondary': '#94A3B8',
        'text-muted': '#64748B',
        gold: {
          DEFAULT: '#F59E0B',
          hover: '#FBBF24',
        },
        success: '#10B981',
        danger: '#EF4444',
        info: '#3B82F6',
      },
      fontFamily: {
        display: ['Outfit', 'sans-serif'],
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        lg: '10px',
        xl: '12px',
        '2xl': '14px',
      },
    },
  },
  plugins: [],
}
