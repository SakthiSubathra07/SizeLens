"""
app/recommend.py  -  Pure Python size-recommendation engine.
No Flask imports. No hardcoded thresholds.
"""

from app.config import MARGIN, MAX_SCORE, CONFIDENCE_HIGH_DIFF, CONFIDENCE_MED_MAX_SCORE


def _deviation(value: float, min_cm: float, max_cm: float) -> float:
    """Return 0 if value is inside [min_cm, max_cm], else distance to nearest edge."""
    if value < min_cm:
        return min_cm - value
    if value > max_cm:
        return value - max_cm
    return 0.0


def recommend(
    measurements: dict,
    rows: list,
    weights: list,
    chart_type: str,
    fit_pref: str = "regular",
) -> dict:
    """
    Compute size recommendations.

    Parameters
    ----------
    measurements : dict
        User's body measurements, e.g. {"chest": 90.0, "shoulder": 40.0}.
        Any key may be absent (optional measurement).
    rows : list[dict]
        Size rows from the database.  Each dict has:
            size_label, measurement, min_cm, max_cm
    weights : list[dict]
        Category weights from the database.  Each dict has:
            measurement, weight, ease_cm
    chart_type : str
        "body" or "garment".
        For garment charts, ease_cm is added to the user's measurement before
        comparing against chart ranges.  Body charts never apply ease.
    fit_pref : str
        "regular" | "slim" | "loose"

    Returns
    -------
    dict with keys:
        best_size     : str | None
        runner_up     : str | None
        scores        : dict[str, float]   size_label -> score
        confidence    : str                "high" | "medium" | "low"
        no_match      : bool
        breakdown     : dict[str, dict]    size_label -> {measurement -> entry}
                        entry has: body_value, min_cm, max_cm, difference
    """

    # ------------------------------------------------------------------
    # 1. Build a weight lookup and determine which measurements are present
    # ------------------------------------------------------------------
    weight_lookup = {w["measurement"]: (w["weight"], w["ease_cm"]) for w in weights}

    present_measurements = {
        m: v for m, v in measurements.items()
        if m in weight_lookup and v is not None
    }

    if not present_measurements:
        return {
            "best_size": None,
            "runner_up": None,
            "scores": {},
            "confidence": "low",
            "no_match": True,
            "breakdown": {},
        }

    # Renormalize weights to sum to 1.0 over present measurements only
    raw_total = sum(weight_lookup[m][0] for m in present_measurements)
    renorm = {m: weight_lookup[m][0] / raw_total for m in present_measurements}

    # ------------------------------------------------------------------
    # 2. Collect all sizes in chart order (preserve insertion order)
    # ------------------------------------------------------------------
    seen_labels = []
    for row in rows:
        lbl = row["size_label"]
        if lbl not in seen_labels:
            seen_labels.append(lbl)

    # ------------------------------------------------------------------
    # 3. Build a nested lookup:  size_label -> measurement -> (min, max)
    # ------------------------------------------------------------------
    chart: dict[str, dict[str, tuple[float, float]]] = {lbl: {} for lbl in seen_labels}
    for row in rows:
        lbl = row["size_label"]
        m = row["measurement"]
        if m in present_measurements:
            chart[lbl][m] = (row["min_cm"], row["max_cm"])

    # ------------------------------------------------------------------
    # 4. Score each size
    # ------------------------------------------------------------------
    scores: dict[str, float] = {}
    breakdowns: dict[str, dict] = {}

    apply_ease = (chart_type == "garment")

    for lbl in seen_labels:
        size_chart = chart[lbl]
        score = 0.0
        breakdown_entry = {}

        for m, body_val in present_measurements.items():
            if m not in size_chart:
                continue
            min_cm, max_cm = size_chart[m]
            ease = weight_lookup[m][1] if apply_ease else 0.0
            effective_val = body_val + ease
            dev = _deviation(effective_val, min_cm, max_cm)
            score += renorm[m] * dev
            breakdown_entry[m] = {
                "body_value": body_val,
                "min_cm": min_cm,
                "max_cm": max_cm,
                "difference": dev,
            }

        scores[lbl] = round(score, 10)   # avoid float noise in comparisons
        breakdowns[lbl] = breakdown_entry

    # ------------------------------------------------------------------
    # 5. Rank sizes by score (ascending), preserving chart order on ties
    # ------------------------------------------------------------------
    ranked = sorted(seen_labels, key=lambda lbl: (scores[lbl], seen_labels.index(lbl)))

    best_label = ranked[0]
    best_score = scores[best_label]

    # No-match check
    if best_score > MAX_SCORE:
        return {
            "best_size": None,
            "runner_up": None,
            "scores": scores,
            "confidence": "low",
            "no_match": True,
            "breakdown": breakdowns,
        }

    runner_up_label = ranked[1] if len(ranked) > 1 else None
    runner_up_score = scores[runner_up_label] if runner_up_label else None

    # ------------------------------------------------------------------
    # 6. Apply fit preference
    # ------------------------------------------------------------------
    chosen_label = best_label

    if fit_pref in ("slim", "loose") and runner_up_label is not None:
        diff = runner_up_score - best_score
        if diff < MARGIN:
            # The two best sizes are within margin — slim/loose can override
            # We work with the two candidates: best and runner-up, in chart order
            two = [best_label, runner_up_label]
            two_by_chart = sorted(two, key=lambda lbl: seen_labels.index(lbl))
            if fit_pref == "slim":
                chosen_label = two_by_chart[0]   # smaller (earlier) size
            else:  # loose
                chosen_label = two_by_chart[-1]  # larger (later) size

    # ------------------------------------------------------------------
    # 7. Confidence
    # ------------------------------------------------------------------
    if runner_up_score is not None:
        gap = runner_up_score - best_score
    else:
        gap = float("inf")

    if best_score == 0.0 and gap >= CONFIDENCE_HIGH_DIFF:
        confidence = "high"
    elif best_score <= CONFIDENCE_MED_MAX_SCORE:
        confidence = "medium"
    else:
        confidence = "low"

    # Determine runner-up for the returned dict (the second-best, not fit-pref-adjusted)
    return {
        "best_size": chosen_label,
        "runner_up": runner_up_label,
        "scores": scores,
        "confidence": confidence,
        "no_match": False,
        "breakdown": breakdowns,
    }
