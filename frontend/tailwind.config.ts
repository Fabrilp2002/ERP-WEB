import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1d4ed8',
          light:   '#2563eb',
          dark:    '#1e40af',
          bg:      '#eff6ff',
          300:     '#93c5fd',
          400:     '#60a5fa',
          500:     '#3b82f6',
          600:     '#2563eb',
          700:     '#1d4ed8',
          800:     '#1e40af',
          900:     '#1e3a8a',
        },
        sidebar:  '#1e293b',
        success:  { DEFAULT: '#16a34a', bg: '#f0fdf4' },
        warning:  { DEFAULT: '#d97706', bg: '#fffbeb' },
        danger:   { DEFAULT: '#dc2626', bg: '#fef2f2' },
        purple:   { DEFAULT: '#7c3aed', bg: '#f5f3ff' },
        surface:  '#f1f5f9',
        border:   '#e2e8f0',
        muted:    '#64748b',
      },
    },
  },
  plugins: [],
}

export default config
