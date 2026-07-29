/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Outfit', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      colors: {
        ai: {
          bg: 'var(--ai-bg)',
          surface: 'var(--ai-surface)',
          'surface-hover': 'var(--ai-surface-hover)',
          input: 'var(--ai-input)',
          text: 'var(--ai-text)',
          'text-secondary': 'var(--ai-text-secondary)',
          'text-muted': 'var(--ai-text-muted)',
          primary: 'var(--ai-primary)',
          'primary-hover': 'var(--ai-primary-hover)',
          'primary-light': 'var(--ai-primary-light)',
          teal: 'var(--ai-teal)',
          'teal-hover': 'var(--ai-teal-hover)',
          'teal-light': 'var(--ai-teal-light)',
          border: 'var(--ai-border)',
          'border-subtle': 'var(--ai-border-subtle)',
        },
      },
      borderRadius: {
        ai: 'var(--ai-radius)',
      },
      boxShadow: {
        ai: 'var(--ai-shadow)',
        'ai-lg': 'var(--ai-shadow-lg)',
      },
    },
  },
  plugins: [],
};
