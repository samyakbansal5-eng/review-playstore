You are analysing public Google Play reviews of apps in the domain: {{DOMAIN}}.
Classify EACH review below. Reviews may be English, Hindi, or Hinglish (Hindi in Latin script) — understand all of them.

THEMES (choose exactly ONE primary theme per review — the main thing the reviewer is talking about):
{{THEMES}}

Rules:
1. Pick the theme of the reviewer's MAIN complaint or topic. If there is a complaint, prefer the theme of the complaint over generic praise.
2. Very short or generic reviews ("good", "nice app", "best") -> "other".
3. Do not infer a problem that the text does not state.
4. sentiment = overall tone of the review: positive, neutral, or negative.
5. features = list of feature ids from the list below that the reviewer explicitly asks for, complains is missing, or praises. Usually empty [].
6. reason = at most 12 words in English explaining the theme choice.

FEATURES (ids only):
{{FEATURES}}

Return ONLY a JSON array, one object per review, in the same order:
[{"id": "<review id>", "theme": "<theme id>", "sentiment": "...", "features": [], "reason": "..."}]

REVIEWS:
{{REVIEWS}}
