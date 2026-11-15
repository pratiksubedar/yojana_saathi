/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#F6F3EC',
        surface: '#FFFCF7',
        ink: {
          DEFAULT: '#1C1917',
          muted: '#57534E',
          light: '#78716C',
        },
        forest: {
          DEFAULT: '#1F4D3A',
          deep: '#143528',
          hover: '#194232',
          light: '#E7EFE8',
        },
        sage: '#E7EFE8',
        sand: {
          DEFAULT: '#E8E1D4',
          light: '#F2ECE1',
        },
        eligible: {
          DEFAULT: '#1F7A4D',
          bg: '#EAF5EE',
          border: '#BDE0CB',
        },
        maybe: {
          DEFAULT: '#9A6B12',
          bg: '#FEF8EA',
          border: '#F6DFAB',
        },
        ineligible: {
          DEFAULT: '#8F3D3D',
          bg: '#FDF0F0',
          border: '#F4C8C8',
        },
        // Backward-compatible design mappings
        brand: {
          indigo: '#1F4D3A',
          'indigo-hover': '#143528',
          'indigo-tint': '#E7EFE8',
          orange: '#9A6B12',
          'orange-tint': '#FEF8EA',
          teal: '#1F7A4D',
          'teal-tint': '#EAF5EE',
        },
        status: {
          green: '#1F7A4D',
          'green-bg': '#EAF5EE',
          amber: '#9A6B12',
          'amber-bg': '#FEF8EA',
          red: '#8F3D3D',
          'red-bg': '#FDF0F0',
        },
        neutral: {
          canvas: '#F6F3EC',
          surface: '#FFFCF7',
          ink: '#1C1917',
          slate: '#57534E',
          mist: '#E8E1D4',
        }
      },
      fontFamily: {
        sans: [
          '"Noto Sans"',
          '"Noto Sans Devanagari"',
          '"Noto Sans Kannada"',
          '"Noto Sans Telugu"',
          'system-ui',
          '-apple-system',
          'sans-serif',
        ],
        heading: [
          '"Noto Sans"',
          '"Noto Sans Devanagari"',
          '"Noto Sans Kannada"',
          '"Noto Sans Telugu"',
          'system-ui',
          'sans-serif',
        ],
      },
      borderRadius: {
        card: '16px',
        button: '14px',
        orb: '9999px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(28, 25, 23, 0.04), 0 1px 2px rgba(28, 25, 23, 0.02)',
        'card-hover': '0 4px 12px rgba(28, 25, 23, 0.06), 0 2px 4px rgba(28, 25, 23, 0.03)',
        orb: '0 8px 30px rgba(31, 77, 58, 0.18)',
        'orb-active': '0 12px 40px rgba(31, 77, 58, 0.28)',
      }
    },
  },
  plugins: [],
};

