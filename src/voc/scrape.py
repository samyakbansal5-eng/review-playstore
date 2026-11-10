"""Scrape public Play Store reviews across a time window and keep a month-stratified random sample.

Why stratify: the newest 5,000 reviews of a huge app cover only a few days, which makes trends
impossible. We stream the last `months_back` months and keep a random quota per month. Each kept
review carries a `weight` (month population / month sample) so overall shares stay unbiased.
"""
import heapq
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from dateutil.relativedelta import relativedelta
from google_play_scraper import Sort, reviews
from .config import load_domain, paths


def scrape_app(a, cfg, log=print):
    cutoff = pd.Timestamp.now() - relativedelta(months=cfg["months_back"])
    quota = math.ceil(cfg["target_per_app"] / cfg["months_back"])
    rng = random.Random(42)
    heaps, pop, rating_sum, rating_n = {}, {}, {}, {}   # month -> reservoir heap / counts
    token, seen, tick = None, 0, 0
    done = False
    while not done:
        for attempt in range(5):
            try:
                batch, token = reviews(a["package"], lang=cfg["lang"], country=cfg["country"],
                                       sort=Sort.NEWEST, count=200, continuation_token=token)
                break
            except Exception as e:
                log(f"  [{a['name']}] retry {attempt+1}: {str(e)[:70]}")
                time.sleep(4 * (attempt + 1))
        else:
            log(f"  [{a['name']}] giving up after repeated errors; keeping what we have")
            break
        if not batch:
            break
        for r in batch:
            if pd.Timestamp(r["at"]) < cutoff:
                done = True
                break
            seen += 1
            m = r["at"].strftime("%Y-%m")
            rating_sum[m] = rating_sum.get(m, 0) + r["score"]
            rating_n[m] = rating_n.get(m, 0) + 1
            text = (r["content"] or "").strip()
            if len(text) < 3:
                continue
            pop[m] = pop.get(m, 0) + 1
            tick += 1
            h = heaps.setdefault(m, [])
            item = (rng.random(), tick, r)           # reservoir via random priority, keep top-k
            if len(h) < quota:
                heapq.heappush(h, item)
            elif item[0] > h[0][0]:
                heapq.heapreplace(h, item)
        if seen and seen % 10000 < 200:
            log(f"  [{a['name']}] scraped {seen:,} reviews (at {batch[-1]['at']:%Y-%m-%d})")
        if token is None:
            break
        time.sleep(0.3)
    rows = []
    for m, h in heaps.items():
        w = pop[m] / len(h)
        for _, _, r in h:
            rows.append({"review_id": r["reviewId"], "app_id": a["id"], "app": a["name"],
                         "text": r["content"].strip(), "rating": r["score"], "date": r["at"],
                         "thumbs_up": r["thumbsUpCount"], "version": r["reviewCreatedVersion"],
                         "month": m, "weight": w})
    monthly = [{"app_id": a["id"], "month": m, "reviews_total": rating_n[m],
                "avg_rating": rating_sum[m] / rating_n[m]} for m in sorted(rating_n)]
    log(f"  [{a['name']}] done: {seen:,} scraped, {len(rows):,} kept")
    return pd.DataFrame(rows), pd.DataFrame(monthly), seen


def run(domain: str):
    cfg, p = load_domain(domain), paths(domain)
    p["sample"].parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=len(cfg["apps"])) as ex:
        results = list(ex.map(lambda a: scrape_app(a, cfg), cfg["apps"]))
    s = pd.concat([r[0] for r in results], ignore_index=True)
    s["date"] = pd.to_datetime(s["date"])
    s = s.drop_duplicates(["app_id", "text"])
    s.to_parquet(p["sample"])
    monthly = pd.concat([r[1] for r in results], ignore_index=True)
    monthly.to_parquet(p["sample"].with_name(f"{domain}_monthly.parquet"))
    print(s.groupby("app").agg(sample=("review_id", "count"), start=("date", "min"), end=("date", "max"),
                               avg_rating=("rating", "mean")).round(2))
    print(f"Population scraped: {sum(r[2] for r in results):,} | analysis sample: {len(s):,} -> {p['sample']}")
