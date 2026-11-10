"""LLM-vs-human agreement on the hand-labelled sample."""
import json
import pandas as pd
from .classify import classify_df, MODEL, PROVIDER
from .config import load_domain, paths


def cohen_kappa(a, b):
    a, b = pd.Series(a).reset_index(drop=True), pd.Series(b).reset_index(drop=True)
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def run(domain: str):
    cfg, p = load_domain(domain), paths(domain)
    labels = pd.read_csv(p["labels"]).rename(columns={"theme": "human"})
    sample = pd.read_csv(p["label_sample"]).merge(labels, on="review_id")
    print(f"{len(sample)} hand-labelled reviews")
    cache = classify_df(cfg, sample, p["preds"].with_name(f"{domain}_eval_{PROVIDER}.jsonl"), label="[eval] ")
    sample["llm"] = sample["review_id"].map(lambda r: cache.get(r, {}).get("theme", "other"))
    acc = (sample["human"] == sample["llm"]).mean()
    kappa = cohen_kappa(sample["human"], sample["llm"])
    per = []
    for t in cfg["themes"]:
        tp = ((sample.human == t["id"]) & (sample.llm == t["id"])).sum()
        fp = ((sample.human != t["id"]) & (sample.llm == t["id"])).sum()
        fn = ((sample.human == t["id"]) & (sample.llm != t["id"])).sum()
        pr, rc = tp / (tp + fp) if tp + fp else None, tp / (tp + fn) if tp + fn else None
        f1 = 2 * pr * rc / (pr + rc) if pr and rc else None
        per.append({"theme": t["id"], "name": t["name"], "support": int((sample.human == t["id"]).sum()),
                    "precision": pr, "recall": rc, "f1": f1})
    ids = cfg["theme_ids"]
    cm = [[int(((sample.human == h) & (sample.llm == l)).sum()) for l in ids] for h in ids]
    res = {"domain": domain, "n_labelled": len(sample), "agreement": acc, "kappa": kappa,
           "model": f"{PROVIDER}:{MODEL}", "per_theme": per, "confusion": {"labels": ids, "matrix": cm}}
    out = p["export"]; out.mkdir(parents=True, exist_ok=True)
    (out / f"{domain}_eval.json").write_text(json.dumps(res, indent=2))
    sample.to_csv(p["preds"].with_name(f"{domain}_eval_detail.csv"), index=False)
    print(f"Agreement {acc:.1%} (kappa {kappa:.2f}) on {len(sample)} reviews [{PROVIDER}:{MODEL}]")
    dis = sample[sample.human != sample.llm]
    for _, r in dis.head(15).iterrows():
        print(f"  human={r.human:16s} llm={r.llm:16s} | {r.text[:90]!r}")
