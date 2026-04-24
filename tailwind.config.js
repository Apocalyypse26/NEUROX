/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: '#000000',
        foreground: '#FFFFFF',
        primary: {
          DEFAULT: '#FF4500',
          hover: '#FF6B35',
          glow: 'rgba(255, 69, 0, 0.4)'
        },
        secondary: '#888888',
        muted: '#444444',
        border: 'rgba(255, 255, 255, 0.06)',
        card: {
          DEFAULT: 'rgba(255, 255, 255, 0.02)',
          hover: 'rgba(255, 255, 255, 0.04)'
        }
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "'Syne'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      letterSpacing: {
        tighter: '-0.04em',
        tight: '-0.02em',
        widest: '0.1em',
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(255, 69, 0, 0.4)',
        'glow-primary-lg': '0 0 30px rgba(255, 69, 0, 0.35)',
        'glow-primary-xl': '0 0 40px rgba(255, 69, 0, 0.5)',
        'glass-card': '0 20px 40px rgba(0, 0, 0, 0.4)',
        'preview-window': '0 0 0 1px rgba(255, 69, 0, 0.1), 0 40px 80px rgba(0, 0, 0, 0.6), inset 0 0 60px rgba(255, 69, 0, 0.05)',
      },
      borderRadius: {
        'card': '16px',
        'btn': '10px',
      },
      transitionTimingFunction: {
        'premium': 'cubic-bezier(0.4, 0, 0.2, 1)',
      }
    },
  },
  plugins: [],
}