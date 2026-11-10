"""Human labelling tool (blind mode or AI-suggested review mode).

`python run.py label-sample --domain upi`  -> draws the review sample to label
`python run.py label --domain upi`         -> opens a local page; one click (or number key) per review

Labels are written to labels/<domain>_labels.csv after every click, so you can stop and resume.
Review mode: `python run.py suggest --domain upi` (run with a stronger model, e.g. LLM_MODEL=gemini-3.5-flash)
stores AI-suggested themes; the page then pre-highlights the suggestion and Enter accepts it. The CSV records
both the human's final theme and the suggestion, so the report can state exactly how many were changed.
The page never shows the star rating.
"""
import csv
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import pandas as pd
from .config import load_domain, paths


def make_sample(domain: str, seed: int = 7):
    cfg, p = load_domain(domain), paths(domain)
    df = pd.read_parquet(p["sample"])
    df = df[df["text"].str.len() >= 12]               # skip one-word reviews that carry no signal
    n_apps = df["app_id"].nunique()
    per_app = -(-cfg["label_sample_size"] // n_apps)
    # Stratify by rating so the hand-labelled set contains plenty of real complaints:
    # 50% 1-2 star, 20% 3 star, 30% 4-5 star (agreement is measured on this mix; documented in the report).
    mix = [((1, 2), 0.5), ((3, 3), 0.2), ((4, 5), 0.3)]
    parts = []
    for _, g in df.groupby("app_id"):
        for (lo, hi), frac in mix:
            gg = g[g.rating.between(lo, hi)]
            parts.append(gg.sample(min(round(per_app * frac), len(gg)), random_state=seed))
    s = pd.concat(parts).sample(frac=1, random_state=seed)      # shuffle so apps are mixed
    s[["review_id", "app", "text"]].to_csv(p["label_sample"], index=False)
    print(f"Label sample: {len(s)} reviews -> {p['label_sample']}")


def suggest(domain: str):
    """Pre-label the label sample with an LLM so a human can review instead of label from scratch."""
    from .classify import classify_df, MODEL
    cfg, p = load_domain(domain), paths(domain)
    df = pd.read_csv(p["label_sample"])
    classify_df(cfg, df, p["label_sample"].with_name(f"{domain}_suggestions.jsonl"), label=f"[suggest:{MODEL}] ")


PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Label reviews</title>
<style>
:root{color-scheme:light dark;--bg:#f6f7fb;--card:#fff;--fg:#111827;--mut:#6b7280;--acc:#4f46e5;--bd:#e5e7eb}
@media(prefers-color-scheme:dark){:root{--bg:#0b0f19;--card:#121826;--fg:#e5e7eb;--mut:#9ca3af;--bd:#243047}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px}
.bar{height:8px;background:var(--bd);border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:var(--acc)}
.meta{display:flex;justify-content:space-between;color:var(--mut);font-size:14px;margin:8px 0 16px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:22px;font-size:19px;min-height:110px;white-space:pre-wrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:16px}
button{all:unset;cursor:pointer;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:12px 14px;box-sizing:border-box}
button:hover{border-color:var(--acc)}button.sug{border:2px solid var(--acc);background:color-mix(in srgb,var(--acc) 10%,var(--card))}.tag{font-size:12px;color:var(--acc);font-weight:600}button b{color:var(--acc);margin-right:8px}
button small{display:block;color:var(--mut);font-size:12px;margin-top:2px}
.nav{margin-top:16px;color:var(--mut);font-size:14px}.nav a{color:var(--acc);cursor:pointer}
</style>
<main><div class=bar><i id=pb></i></div>
<div class=meta><span id=prog></span><span id=app></span></div>
<div class=card id=text></div><div class=grid id=grid></div>
<div class=nav>Enter accepts the highlighted suggestion · keys 1–9 pick a theme · <a onclick=back()>← back</a> · labels save automatically</div></main>
<script>
let D,i=0;
async function load(){D=await (await fetch('/data')).json();i=D.items.findIndex(x=>!D.labels[x.review_id]);if(i<0)i=D.items.length;render()}
function render(){
 const n=D.items.length,done=Object.keys(D.labels).length;
 document.getElementById('pb').style.width=(100*done/n)+'%';
 document.getElementById('prog').textContent=done+' / '+n+' labelled';
 if(i>=n){document.getElementById('text').textContent='All '+n+' labelled. You can close this tab. Thank you!';document.getElementById('grid').innerHTML='';return}
 const it=D.items[i];document.getElementById('app').textContent=it.app;
 document.getElementById('text').textContent=it.text;
 document.getElementById('grid').innerHTML=D.themes.map((t,k)=>`<button class="${t.id===it.suggested?'sug':''}" onclick="pick('${t.id}')"><b>${k+1}</b>${t.name}${t.id===it.suggested?' <span class=tag>· suggested — press Enter</span>':''}<small>${t.definition}</small></button>`).join('')}
async function pick(t){const it=D.items[i];D.labels[it.review_id]=t;
 await fetch('/label',{method:'POST',body:JSON.stringify({review_id:it.review_id,theme:t})});i++;render()}
function back(){if(i>0){i--;render()}}
addEventListener('keydown',e=>{const k=parseInt(e.key);if(k>=1&&k<=D.themes.length&&i<D.items.length)pick(D.themes[k-1].id);if(e.key==='ArrowLeft')back();if(e.key==='Enter'&&i<D.items.length&&D.items[i].suggested)pick(D.items[i].suggested)});
load()
</script>"""


def serve(domain: str, port: int = 8765):
    cfg, p = load_domain(domain), paths(domain)
    if not p["label_sample"].exists():
        make_sample(domain)
    items = pd.read_csv(p["label_sample"]).to_dict("records")
    sug_file = p["label_sample"].with_name(f"{domain}_suggestions.jsonl")
    sugg = {}
    if sug_file.exists():
        for line in sug_file.read_text().splitlines():
            r = json.loads(line); sugg[r["id"]] = r["theme"]
    for it in items:
        it["suggested"] = sugg.get(it["review_id"])
    p["labels"].parent.mkdir(exist_ok=True)

    def read_labels():
        if not p["labels"].exists():
            return {}
        with open(p["labels"], newline="") as f:
            return {r["review_id"]: r["theme"] for r in csv.DictReader(f)}

    def write_labels(d):
        with open(p["labels"], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["review_id", "theme", "suggested"])
            w.writerows((k, v, sugg.get(k, "")) for k, v in d.items())

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, body, ctype="application/json"):
            b = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/data":
                self._send(json.dumps({"items": items, "themes": cfg["themes"], "labels": read_labels()}))
            else:
                self._send(PAGE, "text/html")

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            d = read_labels()
            d[body["review_id"]] = body["theme"]
            write_labels(d)
            self._send("{}")

    srv = HTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}"
    print(f"Labelling {len(items)} reviews at {url}  (Ctrl+C to stop; progress is saved)")
    webbrowser.open(url)
    srv.serve_forever()
