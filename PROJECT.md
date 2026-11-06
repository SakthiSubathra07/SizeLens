# SizeLens: project spec

Web app that recommends a clothing size from body measurements and a
brand-specific size chart. Rule-based, no machine learning.

## Stack
Python 3, Flask, SQLite (sqlite3 module), Jinja templates, plain CSS/JS, pytest.

## Schema
brands(id, name)
categories(id, name)
size_charts(id, brand_id, category_id, chart_type, notes)  -- chart_type: 'body' | 'garment'
size_rows(id, chart_id, size_label, measurement, min_cm, max_cm)
size_availability(chart_id, size_label, in_stock)
category_weights(category_id, measurement, weight, ease_cm)
users(id, email, password_hash)
profiles(user_id, height, chest, shoulder, waist, hip, inseam)
recommendations(id, user_id, chart_id, size_label, score, fit_pref, created_at)

## Algorithm (recommend.py, pure Python, no Flask imports)
- For each size: per measurement, deviation = 0 if value is inside [min,max],
  else distance to the nearest edge. Score = sum(weight * deviation). Lower is better.
- Ease: if chart_type == 'garment', add ease_cm to the user's value before comparing.
  Never add ease for 'body' charts.
- Missing optional measurement: skip it and renormalize the remaining weights.
- Fit preference: regular = lowest score. If the two best scores differ by less than
  MARGIN (1.0), slim picks the smaller size and loose picks the larger one.
- No good match: if the best score > MAX_SCORE (4.0), return no match instead of a size.
- Confidence: high if best score == 0 and runner-up - best >= 1.5; medium if best <= 2;
  else low.
- MARGIN, MAX_SCORE and the confidence cutoffs live in config.py, not inline.
- Return: best size, runner-up, all scores, and per-measurement comparison
  (body value, chart range, difference) for the explanation panel.
- If the recommended size is marked out of stock in `size_availability`, show
  the closest in-stock size by the engine's scores as an alternative. Sizes
  without an availability row are treated as in stock.

## Weights (placeholders, stored in the database)
T-shirt: chest 0.40, shoulder 0.35, waist 0.25. Ease only for garment charts:
chest 10, shoulder 1, waist 10.
Jeans: waist 0.50, hip 0.30, inseam 0.20. No ease.

## Fictional T-shirt data (cm)
UrbanThread (body chart)
  S: chest 82-87, shoulder 37-39, waist 68-73
  M: chest 88-93, shoulder 40-42, waist 74-79
  L: chest 94-99, shoulder 43-45, waist 80-85
  XL: chest 100-105, shoulder 46-48, waist 86-91
NorthLoom (body chart)
  S: chest 86-91, shoulder 39-41, waist 72-77
  M: chest 92-97, shoulder 42-44, waist 78-83
  L: chest 98-103, shoulder 45-47, waist 84-89
  XL: chest 104-109, shoulder 48-50, waist 90-95
PrimeWeave (GARMENT chart)
  S: chest 94-99, shoulder 40-42, waist 80-85
  M: chest 100-105, shoulder 43-45, waist 86-91
  L: chest 106-111, shoulder 46-48, waist 92-97
  XL: chest 112-117, shoulder 49-51, waist 98-103
Jeans: invent plausible fictional charts for the same three brands, sizes 28/30/32/34,
measuring waist, hip and inseam. Use the same body/garment type per brand.

## Required test cases
1. Body chest 90, shoulder 40, waist 74, regular fit, T-shirt:
   UrbanThread -> M, NorthLoom -> S, PrimeWeave -> S (same body, different brands).
2. NorthLoom body chest 92, shoulder 41, waist 77: regular -> S, slim -> S, loose -> M.
3. Value exactly on a range boundary counts as a perfect match for that measurement.
4. Chest 130 -> no good match.
5. Missing waist -> still returns a size using renormalized weights.
6. Garment chart: ease is added; body chart: ease is not added.
7. Result includes runner-up, scores and per-measurement comparison.

## Rules
- Use only the fictional data above. Never invent real brand data.
- Keep weights, ease and thresholds out of code logic.
- Body measurements are personal data: saving is optional and deletable.
- Accounts are optional. Passwords must be stored as Werkzeug password hashes.
- POST forms require CSRF protection. Set the Flask `SECRET_KEY` environment
  variable before starting the application; do not use a committed fallback.
- Logged-in recommendations are retained in the user's history. “Delete my
  data” removes the account, saved profile, and recommendation history.

## Accounts and local setup
Set a unique, private `SECRET_KEY` environment variable before running
`python run.py`. New users can optionally save their measurements by selecting
the checkbox on the size form. Saved measurements prefill future forms, and
recommendations generated while logged in appear on the history page.
