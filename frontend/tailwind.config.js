/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#F8FAFC',
        surface: '#FFFFFF',
        'surface-hover': '#F1F5F9',
        border: '#E2E8F0',
        'border-strong': '#CBD5E1',
        'text-primary': '#0F172A',
        'text-secondary': '#475569',
        'text-muted': '#94A3B8',
        primary: {
          DEFAULT: '#2563EB',
          hover: '#1D4ED8',
        },
        // Alias so existing `text-gold`/`bg-gold` keep working without file churn
        gold: {
          DEFAULT: '#2563EB',
          hover: '#1D4ED8',
        },
        success: '#059669',
        danger: '#DC2626',
        info: '#0284C7',
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
