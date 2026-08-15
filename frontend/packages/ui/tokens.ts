// Verbatim from ../../shared/design-tokens/tokens.json — see architecture doc §17.
// Do not hand-edit values here; edit the JSON source of truth and re-sync.

export const colors = {
  ink: "#1C2B39",
  paper: "#FFFFFF",
  bg: "#F3F2EE",
  bgPanel: "#F6F8F9",
  navyPrimary: "#14213D",
  navyDark: "#0B1526",
  navySoft: "#E9ECF5",
  gold: "#C9A227",
  navy: "#0E1930",
  green: "#2F6F4E",
  red: "#B3382C",
  line: "#E3E1DA",
  lineStrong: "#C9C6BC",
} as const;

export const fonts = {
  display: "'Fraunces', serif",
  body: "'IBM Plex Sans', sans-serif",
  mono: "'IBM Plex Mono', monospace",
  googleFontsUrl:
    "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap",
} as const;
