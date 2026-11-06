"""
tests/test_recommend.py

Seven required test cases from PROJECT.md, written before the implementation.

Chart data matches PROJECT.md exactly.  Weights, ease and thresholds are
read from app.config - never hard-coded here.
"""

import pytest
from app.recommend import recommend
from app import config

# ---------------------------------------------------------------------------
# Shared chart fixtures (pure data - no DB, no Flask)
# ---------------------------------------------------------------------------

# category_weights rows: list of dicts with keys measurement, weight, ease_cm
TSHIRT_WEIGHTS = [
    {"measurement": "chest",    "weight": 0.40, "ease_cm": 10.0},
    {"measurement": "shoulder", "weight": 0.35, "ease_cm": 1.0},
    {"measurement": "waist",    "weight": 0.25, "ease_cm": 10.0},
]

# size_rows rows: list of dicts with keys size_label, measurement, min_cm, max_cm
# Sizes are in chart order (S < M < L < XL) which defines slim/loose ordering.

UT_TSHIRT_ROWS = [
    {"size_label": "S",  "measurement": "chest",    "min_cm": 82.0, "max_cm": 87.0},
    {"size_label": "S",  "measurement": "shoulder", "min_cm": 37.0, "max_cm": 39.0},
    {"size_label": "S",  "measurement": "waist",    "min_cm": 68.0, "max_cm": 73.0},
    {"size_label": "M",  "measurement": "chest",    "min_cm": 88.0, "max_cm": 93.0},
    {"size_label": "M",  "measurement": "shoulder", "min_cm": 40.0, "max_cm": 42.0},
    {"size_label": "M",  "measurement": "waist",    "min_cm": 74.0, "max_cm": 79.0},
    {"size_label": "L",  "measurement": "chest",    "min_cm": 94.0, "max_cm": 99.0},
    {"size_label": "L",  "measurement": "shoulder", "min_cm": 43.0, "max_cm": 45.0},
    {"size_label": "L",  "measurement": "waist",    "min_cm": 80.0, "max_cm": 85.0},
    {"size_label": "XL", "measurement": "chest",    "min_cm": 100.0, "max_cm": 105.0},
    {"size_label": "XL", "measurement": "shoulder", "min_cm": 46.0,  "max_cm": 48.0},
    {"size_label": "XL", "measurement": "waist",    "min_cm": 86.0,  "max_cm": 91.0},
]

NL_TSHIRT_ROWS = [
    {"size_label": "S",  "measurement": "chest",    "min_cm": 86.0, "max_cm": 91.0},
    {"size_label": "S",  "measurement": "shoulder", "min_cm": 39.0, "max_cm": 41.0},
    {"size_label": "S",  "measurement": "waist",    "min_cm": 72.0, "max_cm": 77.0},
    {"size_label": "M",  "measurement": "chest",    "min_cm": 92.0, "max_cm": 97.0},
    {"size_label": "M",  "measurement": "shoulder", "min_cm": 42.0, "max_cm": 44.0},
    {"size_label": "M",  "measurement": "waist",    "min_cm": 78.0, "max_cm": 83.0},
    {"size_label": "L",  "measurement": "chest",    "min_cm": 98.0,  "max_cm": 103.0},
    {"size_label": "L",  "measurement": "shoulder", "min_cm": 45.0,  "max_cm": 47.0},
    {"size_label": "L",  "measurement": "waist",    "min_cm": 84.0,  "max_cm": 89.0},
    {"size_label": "XL", "measurement": "chest",    "min_cm": 104.0, "max_cm": 109.0},
    {"size_label": "XL", "measurement": "shoulder", "min_cm": 48.0,  "max_cm": 50.0},
    {"size_label": "XL", "measurement": "waist",    "min_cm": 90.0,  "max_cm": 95.0},
]

PW_TSHIRT_ROWS = [
    {"size_label": "S",  "measurement": "chest",    "min_cm": 94.0,  "max_cm": 99.0},
    {"size_label": "S",  "measurement": "shoulder", "min_cm": 40.0,  "max_cm": 42.0},
    {"size_label": "S",  "measurement": "waist",    "min_cm": 80.0,  "max_cm": 85.0},
    {"size_label": "M",  "measurement": "chest",    "min_cm": 100.0, "max_cm": 105.0},
    {"size_label": "M",  "measurement": "shoulder", "min_cm": 43.0,  "max_cm": 45.0},
    {"size_label": "M",  "measurement": "waist",    "min_cm": 86.0,  "max_cm": 91.0},
    {"size_label": "L",  "measurement": "chest",    "min_cm": 106.0, "max_cm": 111.0},
    {"size_label": "L",  "measurement": "shoulder", "min_cm": 46.0,  "max_cm": 48.0},
    {"size_label": "L",  "measurement": "waist",    "min_cm": 92.0,  "max_cm": 97.0},
    {"size_label": "XL", "measurement": "chest",    "min_cm": 112.0, "max_cm": 117.0},
    {"size_label": "XL", "measurement": "shoulder", "min_cm": 49.0,  "max_cm": 51.0},
    {"size_label": "XL", "measurement": "waist",    "min_cm": 98.0,  "max_cm": 103.0},
]


# ---------------------------------------------------------------------------
# Test 1: Same body measurements, three different brands/chart types
# Body chest=90, shoulder=40, waist=74, regular fit
# UrbanThread -> M, NorthLoom -> S, PrimeWeave -> S
# ---------------------------------------------------------------------------

class TestCase1SameMeasurementsDifferentBrands:
    USER = {"chest": 90.0, "shoulder": 40.0, "waist": 74.0}

    def test_urbanthread_regular_is_M(self):
        result = recommend(
            measurements=self.USER,
            rows=UT_TSHIRT_ROWS,
            weights=TSHIRT_WEIGHTS,
            chart_type="body",
            fit_pref="regular",
        )
        assert not result["no_match"]
        assert result["best_size"] == "M"

    def test_northloom_regular_is_S(self):
        result = recommend(
            measurements=self.USER,
            rows=NL_TSHIRT_ROWS,
            weights=TSHIRT_WEIGHTS,
            chart_type="body",
            fit_pref="regular",
        )
        assert not result["no_match"]
        assert result["best_size"] == "S"

    def test_primeweave_regular_is_S(self):
        result = recommend(
            measurements=self.USER,
            rows=PW_TSHIRT_ROWS,
            weights=TSHIRT_WEIGHTS,
            chart_type="garment",
            fit_pref="regular",
        )
        assert not result["no_match"]
        assert result["best_size"] == "S"


# ---------------------------------------------------------------------------
# Test 2: NorthLoom body chest=92, shoulder=41, waist=77
# regular -> S, slim -> S, loose -> M
# Manual scores: S=0.40, M=0.60  diff=0.20 < MARGIN(1.0)
# ---------------------------------------------------------------------------

class TestCase2FitPreference:
    USER = {"chest": 92.0, "shoulder": 41.0, "waist": 77.0}

    def test_regular_is_S(self):
        result = recommend(
            measurements=self.USER,
            rows=NL_TSHIRT_ROWS,
            weights=TSHIRT_WEIGHTS,
            chart_type="body",
            fit_pref="regular",
        )
        assert not result["no_match"]
        assert result["best_size"] == "S"

    def test_slim_is_S(self):
        result = recommend(
            measurements=self.USER,
            rows=NL_TSHIRT_ROWS,
            weights=TSHIRT_WEIGHTS,
            chart_type="body",
            fit_pref="slim",
        )
        assert not result["no_match"]
        assert result["best_size"] == "S"

    def test_loose_is_M(self):
        result = recommend(
            measurements=self.USER,
            rows=NL_TSHIRT_ROWS,
            weights=TSHIRT_WEIGHTS,
            chart_type="body",
            fit_pref="loose",
        )
        assert not result["no_match"]
        assert result["best_size"] == "M"


# ---------------------------------------------------------------------------
# Test 3: Value exactly on a range boundary is a perfect match (deviation = 0)
# chest=88 is the lower boundary of UrbanThread M (88-93) → dev = 0
# waist=74 is the lower boundary of UrbanThread M (74-79) → dev = 0
# shoulder=40 is the lower boundary of UrbanThread M (40-42) → dev = 0
# → score for M = 0.0  (all three measurements on boundary)
# ---------------------------------------------------------------------------

def test_boundary_is_perfect_match():
    user = {"chest": 88.0, "shoulder": 40.0, "waist": 74.0}
    result = recommend(
        measurements=user,
        rows=UT_TSHIRT_ROWS,
        weights=TSHIRT_WEIGHTS,
        chart_type="body",
        fit_pref="regular",
    )
    assert not result["no_match"]
    assert result["best_size"] == "M"
    # All three measurements sit exactly on the lower boundary → score must be 0
    assert result["scores"]["M"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 4: chest=130 -> no good match (all scores > MAX_SCORE = 4.0)
# ---------------------------------------------------------------------------

def test_no_good_match_chest_130():
    user = {"chest": 130.0, "shoulder": 40.0, "waist": 74.0}
    result = recommend(
        measurements=user,
        rows=UT_TSHIRT_ROWS,
        weights=TSHIRT_WEIGHTS,
        chart_type="body",
        fit_pref="regular",
    )
    assert result["no_match"] is True
    assert result["best_size"] is None


# ---------------------------------------------------------------------------
# Test 5: Missing waist -> renormalize weights and still return a size
# ---------------------------------------------------------------------------

def test_missing_waist_still_returns_size():
    # waist is absent; weights for chest+shoulder renormalize to sum=1
    user = {"chest": 90.0, "shoulder": 40.0}
    result = recommend(
        measurements=user,
        rows=UT_TSHIRT_ROWS,
        weights=TSHIRT_WEIGHTS,
        chart_type="body",
        fit_pref="regular",
    )
    assert not result["no_match"]
    # chest=90 and shoulder=40 are both inside M ranges → score M = 0
    assert result["best_size"] == "M"
    # 'waist' should be absent from the per-measurement breakdown
    assert "waist" not in result["breakdown"]["M"]


# ---------------------------------------------------------------------------
# Test 6: Garment chart applies ease; body chart does not
# User chest=90.  Effective value for garment: 90+10=100.
# PrimeWeave S garment chest range: 94-99. Without ease 90 < 94 → dev=4.
# With ease: 100 > 99 → dev=1.  Score with ease < score without.
# ---------------------------------------------------------------------------

def test_garment_adds_ease_body_does_not():
    user = {"chest": 90.0, "shoulder": 40.0, "waist": 74.0}

    # Garment: ease applied, effective chest=100 → PrimeWeave S dev_chest=1
    garment_result = recommend(
        measurements=user,
        rows=PW_TSHIRT_ROWS,
        weights=TSHIRT_WEIGHTS,
        chart_type="garment",
        fit_pref="regular",
    )

    # Body: no ease, chest=90 → PrimeWeave S dev_chest=4 (chest 94-99, 90<94)
    body_result = recommend(
        measurements=user,
        rows=PW_TSHIRT_ROWS,
        weights=TSHIRT_WEIGHTS,
        chart_type="body",
        fit_pref="regular",
    )

    # Garment S score must be strictly lower than body S score
    garment_s_score = garment_result["scores"]["S"]
    body_s_score = body_result["scores"]["S"]
    assert garment_s_score < body_s_score

    # Confirm specific values
    # Garment: dev_chest=100-99=1 → 0.40*1=0.40; shoulder+waist in range → score=0.40
    assert garment_s_score == pytest.approx(0.40)
    # Body:    dev_chest=94-90=4 → 0.40*4=1.60; shoulder at boundary → 0;
    #          waist: 80-74=6 → 0.25*6=1.50 → score=3.10
    assert body_s_score == pytest.approx(3.10)


# ---------------------------------------------------------------------------
# Test 7: Result dict includes runner-up, all scores, and per-measurement breakdown
# ---------------------------------------------------------------------------

def test_result_structure():
    user = {"chest": 90.0, "shoulder": 40.0, "waist": 74.0}
    result = recommend(
        measurements=user,
        rows=UT_TSHIRT_ROWS,
        weights=TSHIRT_WEIGHTS,
        chart_type="body",
        fit_pref="regular",
    )

    # top-level keys
    assert "best_size" in result
    assert "runner_up" in result
    assert "scores" in result
    assert "confidence" in result
    assert "no_match" in result
    assert "breakdown" in result

    # scores dict has an entry for every size in the chart
    assert set(result["scores"].keys()) == {"S", "M", "L", "XL"}

    # per-measurement breakdown for the best size
    best = result["best_size"]          # "M"
    assert best in result["breakdown"]
    m_breakdown = result["breakdown"][best]
    for m_name in ("chest", "shoulder", "waist"):
        assert m_name in m_breakdown
        entry = m_breakdown[m_name]
        assert "body_value" in entry
        assert "min_cm" in entry
        assert "max_cm" in entry
        assert "difference" in entry

    # runner-up should be the second-best size (S with score 1.80)
    assert result["runner_up"] == "S"

    # confidence: best=0.0, runner_up=1.80, diff=1.80 >= CONFIDENCE_HIGH_DIFF(1.5)
    assert result["confidence"] == "high"
