/* Tailwind Play CDN configuration — extracted from base.html so the
   Content-Security-Policy needs no per-request nonce (cached pages share it).
   Must load AFTER https://cdn.tailwindcss.com (order preserved in base.html). */
tailwind.config = {
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                serif: ['Playfair Display', 'serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            colors: {
                navy: {
                    50:  '#eef2f7',
                    100: '#d5e0ee',
                    200: '#abbfdd',
                    300: '#7d9ec9',
                    400: '#5580b6',
                    500: '#3a65a0',
                    600: '#2d4f80',
                    700: '#1e3a5f',
                    800: '#162d4a',
                    900: '#0d1f35',
                    950: '#07111e',
                },
                gold: {
                    300: '#f5d87a',
                    400: '#f0c842',
                    500: '#D4A017',
                    600: '#b08010',
                    700: '#8a6010',
                },
            },
            animation: {
                'fade-in-up': 'fadeInUp 0.6s ease-out forwards',
                'fade-in': 'fadeIn 0.4s ease-out forwards',
                'slide-in-left': 'slideInLeft 0.5s ease-out forwards',
                'float': 'float 3s ease-in-out infinite',
            },
            keyframes: {
                fadeInUp: {
                    '0%': { opacity: '0', transform: 'translateY(24px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideInLeft: {
                    '0%': { opacity: '0', transform: 'translateX(-24px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-8px)' },
                },
            },
        }
    }
}
