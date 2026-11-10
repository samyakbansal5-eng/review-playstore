"""LLM classification of reviews into the domain's themes.

Provider-agnostic: Gemini free tier by default, or a local Ollama model (LLM_PROVIDER=ollama).
Reviews are sent in batches; results are appended to a JSONL cache so runs are resumable and cheap
to re-run. The prompt lives in prompts/classify.md so it can be iterated against the hand labels.
"""
import json
import os
import re
import time
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv
from .config import ROOT, load_domain, paths

load_dotenv(ROOT / ".env")
PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
BATCH = int(os.getenv("LLM_BATCH", "20"))
MIN_INTERVAL = float(os.getenv("LLM_MIN_INTERVAL", "4.5"))   # seconds between calls (free-tier friendly)
PROMPT_FILE = ROOT / "prompts" / "classify.md"


def build_prompt(cfg: dict, items: list[dict]) -> str:
    themes = "\n".join(f"- {t['id']}: {t['name']} — {t['definition']}" for t in cfg["themes"])
    feats = "\n".join(f"- {f['id']}: {f['name']}" for f in cfg.get("features", []))
    template = PROMPT_FILE.read_text()
    reviews = json.dumps([{"id": i["review_id"], "text": i["text"][:600]} for i in items], ensure_ascii=False)
    return (template.replace("{{DOMAIN}}", cfg["title"]).replace("{{THEMES}}", themes)
            .replace("{{FEATURES}}", feats).replace("{{REVIEWS}}", reviews))


FALLBACKS = [m for m in os.getenv("LLM_FALLBACKS", "gemini-3.1-flash-lite,gemini-3.5-flash").split(",") if m]


def _call(prompt: str, model: str = None) -> str:
    model = model or MODEL
    if PROVIDER == "ollama":
        r = requests.post("http://localhost:11434/api/chat", timeout=600, json={
            "model": model, "stream": False, "format": "json", "options": {"temperature": 0},
            "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        return r.json()["message"]["content"]
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
    return resp.text


def classify_batch(cfg, items, retries=6):
    prompt = build_prompt(cfg, items)
    valid_t, valid_f = set(cfg["theme_ids"]), set(cfg["feature_ids"])
    for attempt in range(retries):
        try:
            chain = [MODEL] + FALLBACKS
            raw = _call(prompt, chain[attempt % len(chain)] if PROVIDER == "gemini" else MODEL)
            data = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
            if isinstance(data, dict):
                data = data.get("results") or next(iter(data.values()))
            out = {}
            for d in data:
                theme = d.get("theme") if d.get("theme") in valid_t else "other"
                out[str(d["id"])] = {
                    "theme": theme,
                    "sentiment": d.get("sentiment") if d.get("sentiment") in ("positive", "neutral", "negative") else "neutral",
                    "features": [f for f in d.get("features", []) if f in valid_f],
                    "reason": str(d.get("reason", ""))[:200],
                }
            return out
        except Exception as e:
            wait = min(30, 3 * (attempt + 1))
            print(f"  batch error ({str(e)[:90]}); retry in {wait}s")
            time.sleep(wait)
    return {}


def classify_df(cfg, df: pd.DataFrame, cache_path: Path, label="") -> dict:
    """Classify rows of df (needs review_id,text); caches to JSONL; returns {review_id: result}."""
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            r = json.loads(line)
            cache[r["id"]] = r
    todo = [r for r in df.to_dict("records") if r["review_id"] not in cache]
    print(f"{label}{len(df)} reviews, {len(cache)} cached, {len(todo)} to classify "
          f"[{PROVIDER}:{MODEL}, batch {BATCH}]")
    last = 0.0
    with open(cache_path, "a") as f:
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            wait = MIN_INTERVAL - (time.time() - last)
            if wait > 0 and PROVIDER == "gemini":
                time.sleep(wait)
            last = time.time()
            res = classify_batch(cfg, chunk)
            for rid, r in res.items():
                rec = {"id": rid, **r}
                cache[rid] = rec
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if (i // BATCH) % 10 == 0:
                print(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
    return cache


def run(domain: str, limit=None):
    cfg, p = load_domain(domain), paths(domain)
    df = pd.read_parquet(p["sample"])
    if limit:
        df = df.sample(limit, random_state=1)
    cache = classify_df(cfg, df, p["preds"].with_suffix(".jsonl"), label=f"[{domain}] ")
    preds = pd.DataFrame(cache.values()).rename(columns={"id": "review_id"})
    out = df.merge(preds, on="review_id", how="left")
    out["theme"] = out["theme"].fillna("unclassified")
    out.to_parquet(p["preds"])
    print(f"Saved {len(out)} classified reviews -> {p['preds']}")
