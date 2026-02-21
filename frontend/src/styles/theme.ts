/**
 * Central design tokens — kept in sync with index.html :root variables.
 * Import `T` everywhere instead of hardcoding hex values.
 */
export const T = {
  // Brand
  primary:     '#e10098',   // magenta — buttons, active states, accents
  secondary:   '#f8f4f0',   // cream — light card tint

  // Text
  text:        '#000',
  textGray:    '#a6a6a6',   // muted / secondary text

  // Backgrounds
  bgPage:      '#fff',
  bgCard:      '#fff',

  // Borders
  borderLight: '#ebebeb',
  border:      '#e1e1e1',

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
  shadow:      '0 1px 4px rgba(0,0,0,0.07)',
  shadowMd:    '0 4px 24px rgba(0,0,0,0.10)',

  // Shape
  radius:      8,
  radiusSm:    6,
  radiusLg:    12,

  // Logo
  logo: 'https://www.blastness.com/loghi/2342/logowhite.png?fv=1750857063',
} as const
