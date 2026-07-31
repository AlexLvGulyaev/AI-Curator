/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'ai-bg': 'var(--ai-bg)',
        'ai-surface': 'var(--ai-surface)',
        'ai-surface-hover': 'var(--ai-surface-hover)',
        'ai-surface-elevated': 'var(--ai-surface-elevated)',
        'ai-input': 'var(--ai-input)',
        'ai-text': 'var(--ai-text)',
        'ai-text-secondary': 'var(--ai-text-secondary)',
        'ai-text-muted': 'var(--ai-text-muted)',
        'ai-primary': 'var(--ai-primary)',
        'ai-primary-hover': 'var(--ai-primary-hover)',
        'ai-primary-light': 'var(--ai-primary-light)',
        'ai-teal': 'var(--ai-teal)',
        'ai-teal-hover': 'var(--ai-teal-hover)',
        'ai-teal-light': 'var(--ai-teal-light)',
        'ai-success': 'var(--ai-success)',
        'ai-success-light': 'rgba(34, 197, 94, 0.12)',
        'ai-error': 'var(--ai-error)',
        'ai-error-light': 'rgba(239, 68, 68, 0.12)',
        'ai-warning': 'var(--ai-warning)',
        'ai-warning-light': 'rgba(245, 158, 11, 0.12)',
        'ai-info': 'var(--ai-info)',
        'ai-info-light': 'rgba(59, 130, 246, 0.12)',
        'ai-border': 'var(--ai-border)',
        'ai-border-subtle': 'var(--ai-border-subtle)',
      },
      fontFamily: {
        display: 'var(--ai-font-display)',
        body: 'var(--ai-font-body)',
      },
      borderRadius: {
        'ai': 'var(--ai-radius)',
      },
      boxShadow: {
        'ai': 'var(--ai-shadow)',
        'ai-lg': 'var(--ai-shadow-lg)',
      },
    },
  },
  plugins: [],
};
