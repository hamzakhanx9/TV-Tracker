export type Theme = "dark" | "light";

const THEME_STORAGE_KEY = "frame-theme";

export function getStoredTheme(): Theme {
  return localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
}
