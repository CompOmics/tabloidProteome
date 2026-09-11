export const THEME_STORAGE_KEY = "theme-preference";

export function getInitialTheme(): "light" | "dark" {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
