/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Azzir ADMS brand palette, pulled from screenshots.
        brand: {
          navy: {
            50: '#EEF2F7',
            100: '#D7E0EC',
            200: '#A9BBD2',
            300: '#7B96B8',
            400: '#4D719E',
            500: '#274D7E',
            600: '#1A3A66',
            700: '#102C50',
            800: '#0B2440',
            900: '#08182B',
          },
          teal: {
            50: '#E6F4F5',
            100: '#C2E5E8',
            200: '#8FCDD3',
            300: '#5DB5BD',
            400: '#319CA6',
            500: '#1A8B96',
            600: '#15727B',
            700: '#105A61',
            800: '#0B4248',
            900: '#062A2E',
          },
        },
        // Aliases for genetest-era classes still referenced by ported pages
        // (e.g. ShiftList header CTAs). Maps onto the ADMS brand navy so the
        // buttons actually render against a coloured background.
        'genetest-navy': '#102C50',
        surface: {
          0: '#FFFFFF',
          50: '#F7F9FC',
          100: '#F0F3F8',
          200: '#E4E9F1',
          300: '#CCD4E0',
          400: '#9AA6B8',
          500: '#6C7891',
          600: '#4A5468',
          700: '#323A4D',
          800: '#1E2535',
          900: '#0E1320',
        },
        status: {
          // Success / In Stock / Passed / Online / Operational / Verified
          success: '#15803D',
          'success-bg': '#DCFCE7',
          // Warning / Low Stock / Due Today / Pending / Warning
          warning: '#B45309',
          'warning-bg': '#FEF3C7',
          // Danger / Out of Stock / Failed / Rejected / Critical / Overdue
          danger: '#B91C1C',
          'danger-bg': '#FEE2E2',
          // Info / Scheduled / Routine / In Stock
          info: '#1D4ED8',
          'info-bg': '#DBEAFE',
          // Neutral / Awaiting / Draft
          neutral: '#475569',
          'neutral-bg': '#E2E8F0',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 3px 0 rgba(15, 23, 42, 0.06)',
        'card-hover': '0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.06)',
        pop: '0 10px 25px -5px rgba(15, 23, 42, 0.10), 0 8px 10px -6px rgba(15, 23, 42, 0.05)',
      },
      borderRadius: {
        card: '12px',
      },
    },
  },
  plugins: [],
}
