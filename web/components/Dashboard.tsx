"use client";
import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Moon, Sun, Code2, Quote as QuoteIcon, ShieldCheck, Search } from "lucide-react";
import type { Domain, DomainIndex, Evaluation, Recommendation } from "@/lib/types";
import { COLORS, monthLabel, num, pct, themeColor } from "@/lib/util";

const REPO = "https://github.com/samyakbansal5-eng/review-playstore";

async function getJSON<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(path);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

export default function Dashboard() {
  const [index, setIndex] = useState<DomainIndex | null>(null);
  const [domainId, setDomainId] = useState<string>("");
  const [data, setData] = useState<Domain | null>(null);
  const [evalr, setEval] = useState<Evaluation | null>(null);
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.dataset.theme === "dark");
    getJSON<DomainIndex>("/data/index.json").then((i) => {
      setIndex(i);
      setDomainId(i?.domains.find((d) => d.id === "upi") ? "upi" : (i?.domains[0]?.id ?? ""));
    });
  }, []);
  useEffect(() => {
    if (!domainId) return;
    setData(null);
    getJSON<Domain>(`/data/${domainId}.json`).then(setData);
    getJSON<Evaluation>(`/data/${domainId}_eval.json`).then(setEval);
    getJSON<Recommendation[]>(`/data/${domainId}_recs.json`).then(setRecs);
  }, [domainId]);

  const toggle = () => {
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch {}
    setDark(!dark);
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent text-sm text-white">V</span>
            <span className="hidden sm:inline">App Voice-of-Customer</span>
          </div>
          <nav className="hidden gap-5 text-sm text-muted md:flex">
            {[["pain", "Pain points"], ["trend", "Trends"], ["compare", "Compare"], ["gaps", "Feature gaps"], ["recs", "Recommendations"], ["explore", "Explorer"], ["method", "Methodology"]].map(([id, l]) => (
              <a key={id} href={`#${id}`} className="hover:text-fg">{l}</a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <a href={REPO} className="grid h-9 w-9 place-items-center rounded-lg border border-border hover:bg-surface2" aria-label="Source code"><Code2 size={16} /></a>
            <button onClick={toggle} className="grid h-9 w-9 place-items-center rounded-lg border border-border hover:bg-surface2" aria-label="Toggle theme">
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-16 px-4 pb-24 pt-10">
        {!data ? (
          <div className="card p-10 text-center text-muted">Loading analysis…</div>
        ) : (
          <>
            <Hero d={data} e={evalr} index={index} domainId={domainId} setDomainId={setDomainId} />
            <PainPoints d={data} />
            <Trends d={data} />
            <Compare d={data} />
            <Gaps d={data} />
            <Recs d={data} recs={recs} />
            <Explorer d={data} />
            <Method d={data} e={evalr} />
          </>
        )}
      </main>
      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        Built from public Google Play reviews · Pipeline, prompts and hand labels are open-source ·{" "}
        <a className="underline" href={REPO}>View code</a>
      </footer>
    </div>
  );
}

function Section({ id, title, sub, children }: { id: string; title: string; sub?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
      {sub && <p className="mt-1 max-w-3xl text-muted">{sub}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

/* ---------------------------------------------------------------- HERO */
function Hero({ d, e, index, domainId, setDomainId }: { d: Domain; e: Evaluation | null; index: DomainIndex | null; domainId: string; setDomainId: (s: string) => void }) {
  const h = d.headline;
  const topTheme = d.themes.find((t) => t.id === h.top_pain_theme);
  const stats: [string, string, string][] = [
    [num(h.reviews_analysed), "reviews analysed", `of ${num(h.reviews_in_window)} in window`],
    [String(h.apps), "apps compared", d.apps.map((a) => a.name).join(" · ")],
    [e ? pct(e.agreement) : "–", "LLM vs human agreement", e ? `${e.n_labelled} hand-labelled reviews` : "pending"],
    [pct(h.top_pain_share_of_one_star), "of 1★ reviews", topTheme ? `are about ${topTheme.name}` : ""],
  ];
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        {(index?.domains ?? [{ id: domainId, title: d.title, description: "" }]).map((x) => (
          <button key={x.id} onClick={() => setDomainId(x.id)}
            className={`rounded-full border px-4 py-1.5 text-sm transition ${x.id === domainId ? "border-accent bg-accent text-white" : "border-border bg-surface text-muted hover:text-fg"}`}>
            {x.title}
          </button>
        ))}
      </div>
      <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
        What users really complain about in{" "}
        <span className="text-accent">{d.title.toLowerCase()}</span> apps
      </h1>
      <p className="mt-4 max-w-3xl text-lg text-muted">
        {d.description} {num(h.reviews_analysed)} public reviews ({monthLabel(h.months[0])} – {monthLabel(h.months[1])}) classified by an LLM
        and validated against my own hand labels.
      </p>
      <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {stats.map(([big, label, small]) => (
          <div key={label} className="card p-5">
            <div className="text-3xl font-semibold tracking-tight">{big}</div>
            <div className="mt-1 text-sm font-medium">{label}</div>
            <div className="mt-0.5 truncate text-xs text-muted">{small}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- PAIN POINTS */
function PainPoints({ d }: { d: Domain }) {
  const [appId, setAppId] = useState(d.apps[0].id);
  useEffect(() => setAppId(d.apps[0].id), [d]);
  const app = d.apps.find((a) => a.id === appId) ?? d.apps[0];
  const ids = d.themes.map((t) => t.id);
  const rows = app.pain_ranking.map((id) => app.themes.find((t) => t.theme === id)!).filter(Boolean);
  const chart = rows.map((r) => ({ name: r.name, id: r.theme, low: +(r.share_of_low_rating * 100).toFixed(1), all: +(r.share * 100).toFixed(1) }));
  return (
    <Section id="pain" title="Ranked pain points" sub="Share of 1–2★ reviews by theme. The 'rating impact' column shows how far each theme drags the app's average rating below its overall mean.">
      <Tabs items={d.apps.map((a) => ({ id: a.id, label: a.name }))} value={appId} onChange={setAppId} />
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <div className="card p-5 lg:col-span-3">
          <div className="mb-2 text-sm text-muted">% of {app.name}'s 1–2★ reviews</div>
          <ResponsiveContainer width="100%" height={Math.max(260, chart.length * 46)}>
            <BarChart data={chart} layout="vertical" margin={{ left: 10, right: 30 }}>
              <CartesianGrid horizontal={false} />
              <XAxis type="number" unit="%" />
              <YAxis type="category" dataKey="name" width={150} />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={tip} />
              <Bar dataKey="low" name="Share of 1–2★ reviews" radius={[0, 6, 6, 0]} label={{ position: "right", fill: "var(--muted)", fontSize: 12, formatter: (v: unknown) => `${v}%` }}>
                {chart.map((c) => <Cell key={c.id} fill={themeColor(ids, c.id)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card overflow-hidden lg:col-span-2">
          <table className="w-full text-sm">
            <thead className="bg-surface2 text-left text-xs uppercase tracking-wide text-muted">
              <tr><th className="p-3">Theme</th><th className="p-3 text-right">Avg ★</th><th className="p-3 text-right">Impact</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.theme} className="border-t border-border">
                  <td className="p-3"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: themeColor(ids, r.theme) }} />{r.name}</td>
                  <td className="p-3 text-right tabular-nums">{r.avg_rating?.toFixed(2) ?? "–"}</td>
                  <td className={`p-3 text-right tabular-nums ${(r.rating_gap ?? 0) < 0 ? "text-bad" : "text-good"}`}>
                    {r.rating_gap == null ? "–" : `${r.rating_gap > 0 ? "+" : ""}${r.rating_gap.toFixed(2)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-border p-3 text-xs text-muted">
            {app.name}: avg rating {app.avg_rating.toFixed(2)} · {pct(app.pct_one_star)} are 1★ · {num(app.reviews_analysed)} reviews analysed
          </div>
        </div>
      </div>
    </Section>
  );
}

const tip = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--fg)" };

function Tabs({ items, value, onChange }: { items: { id: string; label: string }[]; value: string; onChange: (s: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((i) => (
        <button key={i.id} onClick={() => onChange(i.id)}
          className={`rounded-lg px-3.5 py-1.5 text-sm transition ${value === i.id ? "bg-accentsoft font-medium text-accent" : "text-muted hover:bg-surface2 hover:text-fg"}`}>
          {i.label}
        </button>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- TRENDS */
function Trends({ d }: { d: Domain }) {
  const painThemes = d.themes.filter((t) => t.pain);
  const [appId, setAppId] = useState(d.apps[0].id);
  const [selected, setSelected] = useState<string[]>([]);
  useEffect(() => { setAppId(d.apps[0].id); setSelected(painThemes.slice(0, 3).map((t) => t.id)); }, [d]);
  const ids = d.themes.map((t) => t.id);
  const rows = d.trend.filter((r) => r.app === appId).map((r) => ({
    month: monthLabel(r.month), rating: r.avg_rating, volume: r.reviews_total,
    ...Object.fromEntries(Object.entries(r.share).map(([k, v]) => [k, +(v * 100).toFixed(1)])),
  }));
  return (
    <Section id="trend" title="Trends over time" sub="Monthly share of reviews by theme (re-weighted to the true monthly review mix). Pick themes to overlay; the lower chart shows the app's actual average rating.">
      <Tabs items={d.apps.map((a) => ({ id: a.id, label: a.name }))} value={appId} onChange={setAppId} />
      <div className="mt-3 flex flex-wrap gap-2">
        {painThemes.map((t) => {
          const on = selected.includes(t.id);
          return (
            <button key={t.id} onClick={() => setSelected(on ? selected.filter((x) => x !== t.id) : [...selected, t.id])}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition ${on ? "border-transparent text-white" : "border-border text-muted"}`}
              style={on ? { background: themeColor(ids, t.id) } : undefined}>
              {t.name}
            </button>
          );
        })}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <div className="mb-2 text-sm text-muted">% of reviews by theme</div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={rows}>
              <CartesianGrid vertical={false} /><XAxis dataKey="month" /><YAxis unit="%" />
              <Tooltip contentStyle={tip} formatter={(v) => `${v}%`} /><Legend />
              {selected.map((id) => (
                <Line key={id} type="monotone" dataKey={id} name={d.themes.find((t) => t.id === id)?.name} stroke={themeColor(ids, id)} strokeWidth={2.5} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-5">
          <div className="mb-2 text-sm text-muted">Average rating (all reviews that month)</div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={rows}>
              <CartesianGrid vertical={false} /><XAxis dataKey="month" /><YAxis domain={[1, 5]} />
              <Tooltip contentStyle={tip} />
              <Line type="monotone" dataKey="rating" name="Avg rating" stroke="var(--accent)" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- COMPARE */
function Compare({ d }: { d: Domain }) {
  const themes = d.themes;
  const max = Math.max(...d.apps.flatMap((a) => a.themes.map((t) => t.share)));
  return (
    <Section id="compare" title="App vs app" sub="Share of each app's reviews by theme. Darker = a bigger slice of what that app's users talk about.">
      <div className="card overflow-x-auto p-2">
        <table className="w-full min-w-[640px] text-sm">
          <thead><tr><th className="p-3 text-left text-xs uppercase tracking-wide text-muted">Theme</th>
            {d.apps.map((a) => <th key={a.id} className="p-3 text-center font-medium">{a.name}</th>)}</tr></thead>
          <tbody>
            {themes.map((t) => (
              <tr key={t.id} className="border-t border-border">
                <td className="p-3 font-medium">{t.name}</td>
                {d.apps.map((a) => {
                  const v = a.themes.find((x) => x.theme === t.id)?.share ?? 0;
                  return (
                    <td key={a.id} className="p-1.5">
                      <div className="rounded-lg py-2.5 text-center tabular-nums" style={{ background: `color-mix(in srgb, var(--accent) ${Math.round((v / max) * 85)}%, transparent)`, color: v / max > 0.55 ? "#fff" : "var(--fg)" }}>
                        {pct(v, 1)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr className="border-t border-border text-muted">
              <td className="p-3">Average rating</td>
              {d.apps.map((a) => <td key={a.id} className="p-3 text-center tabular-nums">{a.avg_rating.toFixed(2)}★</td>)}
            </tr>
          </tbody>
        </table>
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- FEATURE GAPS */
function Gaps({ d }: { d: Domain }) {
  const feats = Array.from(new Set(d.feature_matrix.map((c) => c.feature)));
  const cell = (app: string, f: string) => d.feature_matrix.find((c) => c.app === app && c.feature === f);
  const max = Math.max(...d.feature_matrix.map((c) => c.mention_rate), 0.0001);
  const sorted = feats.slice().sort((a, b) => d.apps.reduce((s, x) => s + (cell(x.id, b)?.mention_rate ?? 0), 0) - d.apps.reduce((s, x) => s + (cell(x.id, a)?.mention_rate ?? 0), 0));
  return (
    <Section id="gaps" title="Feature gap matrix" sub="How often reviewers bring up each capability (asking for it, missing it, or praising it). Red numbers are the share of those mentions that are negative — high mention + high negativity = unmet demand.">
      <div className="card overflow-x-auto p-2">
        <table className="w-full min-w-[640px] text-sm">
          <thead><tr><th className="p-3 text-left text-xs uppercase tracking-wide text-muted">Capability</th>
            {d.apps.map((a) => <th key={a.id} className="p-3 text-center font-medium">{a.name}</th>)}</tr></thead>
          <tbody>
            {sorted.map((f) => (
              <tr key={f} className="border-t border-border">
                <td className="p-3 font-medium">{d.feature_matrix.find((c) => c.feature === f)?.name}</td>
                {d.apps.map((a) => {
                  const c = cell(a.id, f);
                  const v = c?.mention_rate ?? 0;
                  return (
                    <td key={a.id} className="p-1.5">
                      <div className="rounded-lg px-2 py-2 text-center" style={{ background: `color-mix(in srgb, var(--c2) ${Math.round((v / max) * 70)}%, transparent)` }}>
                        <div className="tabular-nums">{pct(v, 1)}</div>
                        <div className="text-[11px] text-bad">{c && c.mentions >= 5 ? `${pct(c.pct_negative)} neg` : c ? `n=${c.mentions}` : ""}</div>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- RECOMMENDATIONS */
function Recs({ d, recs }: { d: Domain; recs: Recommendation[] | null }) {
  if (!recs?.length) return null;
  const tone = (v: string, invert = false) => ((v === "High") !== invert ? "text-good" : v === "Medium" ? "text-muted" : "text-bad");
  return (
    <Section id="recs" title="Three product recommendations" sub="Each is grounded in the numbers above and in what users actually wrote.">
      <div className="grid gap-4 lg:grid-cols-3">
        {recs.map((r, i) => (
          <article key={i} className="card flex flex-col p-6">
            <div className="text-xs font-semibold uppercase tracking-wide text-accent">Recommendation {i + 1}</div>
            <h3 className="mt-2 text-lg font-semibold leading-snug">{r.title}</h3>
            <p className="mt-2 text-sm text-muted">{r.problem}</p>
            <ul className="mt-4 space-y-2 text-sm">
              {r.evidence.map((e, k) => <li key={k} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />{e}</li>)}
            </ul>
            {r.quotes?.slice(0, 2).map((q, k) => (
              <blockquote key={k} className="mt-3 rounded-xl bg-surface2 p-3 text-sm italic text-muted">
                <QuoteIcon size={12} className="mb-1 inline" /> “{q.text}” <span className="not-italic">— {q.app}</span>
              </blockquote>
            ))}
            <div className="mt-auto grid grid-cols-3 gap-2 pt-5 text-center text-xs">
              <div className="rounded-lg bg-surface2 p-2"><div className="text-muted">Impact</div><div className={`font-semibold ${tone(r.impact)}`}>{r.impact}</div></div>
              <div className="rounded-lg bg-surface2 p-2"><div className="text-muted">Effort</div><div className={`font-semibold ${tone(r.effort, true)}`}>{r.effort}</div></div>
              <div className="rounded-lg bg-surface2 p-2"><div className="text-muted">Metric</div><div className="font-semibold leading-tight">{r.metric}</div></div>
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- EXPLORER */
function Explorer({ d }: { d: Domain }) {
  const [app, setApp] = useState("all");
  const [theme, setTheme] = useState("all");
  const [rating, setRating] = useState("all");
  const [q, setQ] = useState("");
  const [limit, setLimit] = useState(20);
  const ids = d.themes.map((t) => t.id);
  const rows = useMemo(() => d.explorer.filter((r) =>
    (app === "all" || r.app === app) && (theme === "all" || r.theme === theme) &&
    (rating === "all" || r.rating === +rating) && (!q || r.text.toLowerCase().includes(q.toLowerCase()))), [d, app, theme, rating, q]);
  const sel = "rounded-lg border border-border bg-surface px-3 py-2 text-sm";
  return (
    <Section id="explore" title="Review explorer" sub="A random sample of the classified reviews. Filter and read the raw voice of the customer.">
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1"><Search size={14} className="absolute left-3 top-3 text-muted" />
          <input value={q} onChange={(e) => { setQ(e.target.value); setLimit(20); }} placeholder="Search text…" className={`${sel} w-full pl-8`} /></div>
        <select className={sel} value={app} onChange={(e) => { setApp(e.target.value); setLimit(20); }}><option value="all">All apps</option>{d.apps.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
        <select className={sel} value={theme} onChange={(e) => { setTheme(e.target.value); setLimit(20); }}><option value="all">All themes</option>{d.themes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
        <select className={sel} value={rating} onChange={(e) => { setRating(e.target.value); setLimit(20); }}><option value="all">Any rating</option>{[1, 2, 3, 4, 5].map((r) => <option key={r} value={r}>{r}★</option>)}</select>
      </div>
      <div className="mt-2 text-sm text-muted">{num(rows.length)} reviews match</div>
      <div className="mt-3 space-y-2">
        {rows.slice(0, limit).map((r, i) => (
          <div key={i} className="card flex gap-3 p-4">
            <div className="w-14 shrink-0 text-center"><div className="text-lg font-semibold">{r.rating}★</div><div className="text-[11px] text-muted">{r.date.slice(0, 7)}</div></div>
            <div className="min-w-0 flex-1">
              <p className="text-sm">{r.text}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                <span className="rounded-full bg-surface2 px-2 py-0.5">{d.apps.find((a) => a.id === r.app)?.name}</span>
                <span className="rounded-full px-2 py-0.5 text-white" style={{ background: themeColor(ids, r.theme) }}>{d.themes.find((t) => t.id === r.theme)?.name}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      {limit < rows.length && <button onClick={() => setLimit(limit + 20)} className="mt-4 rounded-lg border border-border px-4 py-2 text-sm hover:bg-surface2">Show more</button>}
    </Section>
  );
}

/* ---------------------------------------------------------------- METHODOLOGY */
function Method({ d, e }: { d: Domain; e: Evaluation | null }) {
  const ids = d.themes.map((t) => t.id);
  return (
    <Section id="method" title="Methodology & trust" sub="How the numbers were produced, and how far to trust them.">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <div className="flex items-center gap-2 font-semibold"><ShieldCheck size={18} className="text-good" /> Human validation</div>
          {e ? (
            <>
              <div className="mt-3 flex items-end gap-6">
                <div><div className="text-4xl font-semibold">{pct(e.agreement, 1)}</div><div className="text-sm text-muted">agreement with {e.n_labelled} hand labels</div></div>
                <div><div className="text-2xl font-semibold">{e.kappa.toFixed(2)}</div><div className="text-sm text-muted">Cohen's κ</div></div>
              </div>
              <p className="mt-3 text-sm text-muted">Model: <code>{e.model}</code>. I labelled a random sample blind (no model output or star rating shown), then tuned the prompt until agreement was acceptable.{e.notes ? ` ${e.notes}` : ""}</p>
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted"><tr><th className="py-1">Theme</th><th className="text-right">n</th><th className="text-right">Prec.</th><th className="text-right">Recall</th></tr></thead>
                <tbody>{e.per_theme.filter((t) => t.support > 0).map((t) => (
                  <tr key={t.theme} className="border-t border-border"><td className="py-1.5">{t.name}</td><td className="text-right tabular-nums">{t.support}</td><td className="text-right tabular-nums">{pct(t.precision)}</td><td className="text-right tabular-nums">{pct(t.recall)}</td></tr>
                ))}</tbody>
              </table>
            </>
          ) : <p className="mt-3 text-sm text-muted">Validation for this domain is not published yet.</p>}
        </div>
        <div className="card p-6">
          <div className="font-semibold">How it works</div>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-muted">
            <li>Scrape the last 12 months of public Play Store reviews (India) with <code>google-play-scraper</code>.</li>
            <li>Keep an equal random quota per month so trends are visible; re-weight so overall shares match the true mix.</li>
            <li>An LLM assigns each review one theme, a sentiment and any feature mentioned, using theme definitions I wrote.</li>
            <li>Agreement is measured on reviews I labelled by hand; the prompt was iterated until it was acceptable.</li>
            <li>Rating impact = a theme's average rating minus the app's overall average.</li>
          </ol>
          <div className="mt-5 font-semibold">Theme definitions</div>
          <ul className="mt-2 space-y-1.5 text-sm text-muted">
            {d.themes.map((t) => <li key={t.id}><span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: themeColor(ids, t.id) }} /><b className="text-fg">{t.name}</b> — {t.definition}</li>)}
          </ul>
          <div className="mt-5 text-sm font-semibold">Limitations</div>
          <p className="mt-1 text-sm text-muted">Play Store reviewers skew toward people with problems and toward Android users. Reviews show what users complain about, not how many total users are affected. Single-label themes simplify reviews that mention several issues.</p>
          <p className="mt-3 text-sm text-muted">Want another category? Add a YAML file under <code>domains/</code> with apps, themes and features, then run the pipeline — see the repo README.</p>
        </div>
      </div>
    </Section>
  );
}
