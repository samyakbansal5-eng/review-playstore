"""Turn classified reviews into the JSON the dashboard reads (web/public/data/<domain>.json).

All shares are weighted by `weight` (month population / month sample) so the month-stratified
sample still represents each app's true review mix over the window.
"""
import json
import numpy as np
import pandas as pd
from .config import load_domain, paths


def wshare(df, by, weight="weight"):
    """Weighted share of rows per `by` value."""
    s = df.groupby(by)[weight].sum()
    return (s / s.sum()) if s.sum() else s


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def run(domain: str):
    cfg, p = load_domain(domain), paths(domain)
    df = pd.read_parquet(p["preds"])
    df = df[df["theme"] != "unclassified"].copy()
    monthly = pd.read_parquet(p["sample"].with_name(f"{domain}_monthly.parquet"))
    themes = {t["id"]: t for t in cfg["themes"]}
    pain_ids = [t["id"] for t in cfg["themes"] if t.get("pain", True)]
    out_dir = p["export"]; out_dir.mkdir(parents=True, exist_ok=True)

    apps = []
    for a in cfg["apps"]:
        g = df[df.app_id == a["id"]]
        if g.empty:
            continue
        m = monthly[monthly.app_id == a["id"]]
        overall_avg = np.average(g.rating, weights=g.weight)
        share = wshare(g, "theme")
        low = g[g.rating <= 2]
        one = g[g.rating == 1]
        share_low, share_one = wshare(low, "theme"), wshare(one, "theme")
        theme_rows = []
        for tid, t in themes.items():
            tg = g[g.theme == tid]
            avg = np.average(tg.rating, weights=tg.weight) if len(tg) else None
            theme_rows.append({
                "theme": tid, "name": t["name"], "pain": t.get("pain", True), "n": int(len(tg)),
                "share": r4(share.get(tid, 0)),
                "share_of_low_rating": r4(share_low.get(tid, 0)),
                "share_of_one_star": r4(share_one.get(tid, 0)),
                "avg_rating": r4(avg),
                "rating_gap": r4(avg - overall_avg) if avg is not None else None,
                "pct_negative_sentiment": r4(np.average(tg.sentiment == "negative", weights=tg.weight)) if len(tg) else None,
            })
        ranked = sorted([r for r in theme_rows if r["pain"]], key=lambda r: -(r["share_of_low_rating"] or 0))
        apps.append({
            "id": a["id"], "name": a["name"], "package": a["package"],
            "reviews_analysed": int(len(g)),
            "reviews_in_window": int(m.reviews_total.sum()),
            "avg_rating": r4(overall_avg),
            "pct_one_star": r4(np.average(g.rating == 1, weights=g.weight)),
            "themes": theme_rows,
            "pain_ranking": [r["theme"] for r in ranked],
        })

    # ---- monthly trend: theme share per app per month (+ true volume & avg rating)
    trend = []
    for (app_id, month), g in df.groupby(["app_id", "month"]):
        sh = wshare(g, "theme")
        mm = monthly[(monthly.app_id == app_id) & (monthly.month == month)]
        trend.append({"app": app_id, "month": month, "n": int(len(g)),
                      "avg_rating": r4(mm.avg_rating.iloc[0]) if len(mm) else None,
                      "reviews_total": int(mm.reviews_total.iloc[0]) if len(mm) else None,
                      "share": {t: r4(sh.get(t, 0)) for t in themes}})
    trend.sort(key=lambda r: (r["app"], r["month"]))

    # ---- feature gap matrix: weighted share of reviews mentioning each feature, and how negative
    feats = {f["id"]: f for f in cfg.get("features", [])}
    matrix = []
    for a in apps:
        g = df[df.app_id == a["id"]]
        for fid, f in feats.items():
            has = g.features.apply(lambda x: fid in list(x) if x is not None else False)
            sub = g[has]
            matrix.append({
                "app": a["id"], "feature": fid, "name": f["name"], "mentions": int(len(sub)),
                "mention_rate": r4(g.weight[has].sum() / g.weight.sum()),
                "avg_rating": r4(np.average(sub.rating, weights=sub.weight)) if len(sub) else None,
                "pct_negative": r4(np.average(sub.sentiment == "negative", weights=sub.weight)) if len(sub) else None,
            })

    # ---- evidence quotes: most-upvoted low-rating reviews per app x pain theme
    quotes = {}
    for a in apps:
        for tid in pain_ids:
            q = df[(df.app_id == a["id"]) & (df.theme == tid) & (df.rating <= 2)]
            q = q.assign(len_ok=q.text.str.len().between(40, 280)).query("len_ok")
            q = q.sort_values(["thumbs_up", "date"], ascending=False).head(4)
            quotes[f"{a['id']}|{tid}"] = [
                {"text": r.text, "rating": int(r.rating), "date": r.date.strftime("%Y-%m-%d"), "thumbs_up": int(r.thumbs_up)}
                for r in q.itertuples()]

    # ---- explorer sample (kept small so the site stays fast)
    ex = df.sample(min(2500, len(df)), random_state=3)
    explorer = [{"app": r.app_id, "theme": r.theme, "rating": int(r.rating), "date": r.date.strftime("%Y-%m-%d"),
                 "sentiment": r.sentiment, "text": r.text[:320]} for r in ex.itertuples()]

    # ---- domain-level headline numbers
    all_one = df[df.rating == 1]
    pooled = wshare(all_one[all_one.theme.isin(pain_ids)], "theme")
    top = pooled.sort_values(ascending=False)
    headline = {
        "reviews_analysed": int(len(df)),
        "reviews_in_window": int(monthly.reviews_total.sum()),
        "apps": len(apps),
        "top_pain_theme": top.index[0] if len(top) else None,
        "top_pain_share_of_one_star": r4(wshare(all_one, "theme").get(top.index[0], 0)) if len(top) else None,
        "months": [df.month.min(), df.month.max()],
    }

    doc = {
        "domain": domain, "title": cfg["title"], "description": cfg["description"],
        "themes": [{"id": t["id"], "name": t["name"], "definition": t["definition"], "pain": t.get("pain", True)}
                   for t in cfg["themes"]],
        "headline": headline, "apps": apps, "trend": trend, "feature_matrix": matrix,
        "quotes": quotes, "explorer": explorer,
    }
    (out_dir / f"{domain}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {out_dir / (domain + '.json')} — {headline}")
    write_index()


def write_index():
    """List every domain that has exported data, for the dashboard's domain switcher."""
    from .config import DOMAINS_DIR
    import yaml
    out = paths("x")["export"]
    domains = []
    for y in sorted(DOMAINS_DIR.glob("*.yaml")):
        c = yaml.safe_load(y.read_text())
        if (out / f"{c['domain']}.json").exists():
            domains.append({"id": c["domain"], "title": c["title"], "description": c["description"]})
    # flagship domain first
    domains.sort(key=lambda d: d["id"] != "upi")
    (out / "index.json").write_text(json.dumps({"domains": domains}))
