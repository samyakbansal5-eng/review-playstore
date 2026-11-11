# App Voice-of-Customer Engine

What do users actually complain about in fintech apps? This project scrapes public Google Play reviews, classifies each one into themes with an LLM, validates the classifier against human-reviewed labels, and publishes a dashboard with ranked pain points, trends, a feature-gap matrix and product recommendations.

**Two domains shipped, any number possible:** UPI payments (PhonePe, Google Pay, Paytm, Kiwi) and investing apps (Zerodha Kite, Groww, Upstox, Angel One). A domain is one YAML file.

## Headline numbers
| | UPI | Investing |
|---|---|---|
| Reviews in last 12 months (scraped) | 413,213 | 103,944 |
| Reviews classified | 10,625 | 6,690 |
| LLM agreement with human-reviewed labels | **91.0%** on 200 (κ 0.89) | **94.2%** on 52 (κ 0.93) |
| Top pain point | App performance & UX, 21.6% of 1★ reviews | App performance & UX, 24.7% of 1★ reviews |

Findings include: Kiwi's onboarding/KYC is 4% of its reviews but 25% of its 1★ reviews; support and failed-payment complaints carry the steepest rating drag at PhonePe, Google Pay and Paytm; fee transparency is the top 1★ driver at Upstox. Each of the 3 recommendations per domain is on the dashboard with the evidence.

## How the labels were made (read this)
I did **not** label from scratch. A different Gemini model pre-labelled 252 sampled reviews, and I reviewed each in a small local tool (`src/voc/labeling.py`), changing 2 of 200 UPI suggestions and 0 of 52 investing ones. The agreement figures therefore measure consistency with a second model plus human review, **not** fully independent human labelling. The sample is stratified by rating (50% 1–2★, 20% 3★, 30% 4–5★), so agreement is measured on a complaint-heavy mix. Reviews are labelled with a single primary theme.

## Other limitations
- Play Store reviewers skew toward users with problems; reviews show what people complain about, not how many users are affected.
- 870 UPI reviews (820 Kiwi, 50 Google Pay) and 50 Upstox reviews were not classified when the free LLM quota ran out. Weights were re-scaled within each app-month so shares stay representative.
- "Other / unclear" (short praise, spam) is 45–63% of UPI reviews and is excluded from pain-point rankings.
- Some theme assignments are debatable (e.g. praise for support counted under Customer support).

## Method
1. **Scrape** (`google-play-scraper`, India, English): stream the last 12 months and keep a random quota per month (month-stratified) so trends are visible even for apps with 600+ reviews/day. Each review gets a weight (month population / sample) so overall shares are unbiased.
2. **Classify**: Gemini free tier (`gemini-3.5-flash-lite`, fallback models), 25 reviews/request, JSON output: primary theme, sentiment, feature mentions, short reason. Prompt: `prompts/classify.md`. Theme definitions: `domains/*.yaml`.
3. **Validate**: `python run.py evaluate` — accuracy, Cohen's κ, per-theme precision/recall, confusion matrix.
4. **Analyse**: weighted theme shares, share of 1–2★ and 1★ reviews per theme, rating impact (theme avg − app avg), monthly trend, feature-gap matrix, evidence quotes.
5. **Dashboard**: static Next.js site (`web/`) reading the exported JSON; deployed on Vercel.

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # add a free Gemini key from aistudio.google.com
.venv/bin/python run.py scrape --domain upi
.venv/bin/python run.py label-sample --domain upi && .venv/bin/python run.py suggest --domain upi
.venv/bin/python run.py label --domain upi        # review labels in the browser
.venv/bin/python run.py evaluate --domain upi
.venv/bin/python run.py classify --domain upi
.venv/bin/python run.py analyze --domain upi
cd web && npm install && npm run dev
```
Set `LLM_PROVIDER=ollama` and `LLM_MODEL=qwen2.5:7b` to run fully local and free.

## Add your own domain
Copy `domains/upi.yaml`, change the apps (Play Store package IDs), themes (with definitions) and feature list, then run the commands above with `--domain yourname`. The dashboard picks it up automatically.
