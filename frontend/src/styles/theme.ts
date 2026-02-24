/**
 * Central design tokens — kept in sync with index.html :root variables.
 * Import `T` everywhere instead of hardcoding hex values.
 */
export const T = {
  // Brand
  primary:     '#e10098',   // magenta — buttons, active states, accents
  secondary:   '#f8f4f0',   // cream — light card tint

  // Text
  text:        '#111',
  textGray:    '#6b6b6b',   // muted — contrast 5.7:1 on white (WCAG AA)

  // Backgrounds
  bgPage:      '#fff',
  bgCard:      '#fff',
  bgMuted:     '#f7f7f7',   // subtle section bg / alternating rows

  // Borders
  borderLight: '#e4e4e4',   // card borders, dividers
  border:      '#c4c4c4',   // input borders, visible outlines

  // Palette extras
  blue:        '#576a8f',
  lightBlue:   '#697a9b',
  yellow:      '#d6de85',

  // Semantic
  success:     '#059669',
  error:       '#dc2626',
  warning:     '#d97706',

  // Nav
  navBg:       '#000',

  // Elevation
  shadow:      '0 1px 6px rgba(0,0,0,0.10)',
  shadowMd:    '0 4px 20px rgba(0,0,0,0.13)',

  // Shape
  radius:      8,
  radiusSm:    6,
  radiusLg:    12,

  // Logos (served from /public)
  logoBlastness: '/logofooter.png',
  logoApp:       '/AdAtelier.svg',
} as const
