export const pct = (x: number | null | undefined, d = 0) => (x == null ? "–" : `${(x * 100).toFixed(d)}%`);
export const num = (x: number) => x.toLocaleString("en-IN");
export const COLORS = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)", "var(--c6)", "var(--c7)", "var(--c8)", "var(--c9)"];
export const themeColor = (ids: string[], id: string) => COLORS[Math.max(0, ids.indexOf(id)) % COLORS.length];
export const monthLabel = (m: string) => {
  const [y, mo] = m.split("-");
  return new Date(+y, +mo - 1, 1).toLocaleString("en", { month: "short", year: "numeric" });
};
