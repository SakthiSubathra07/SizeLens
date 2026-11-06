"""
tests/test_routes.py

Flask test-client tests for the find_size and result routes.
Uses a seeded temp-database so tests are hermetic.
"""

import re
import uuid

import pytest
from app import create_app
from seed import seed_database


@pytest.fixture(scope='module')
def seeded_app(tmp_path_factory):
    """Create a Flask app wired to a seeded temp database."""
    db_path = tmp_path_factory.mktemp('db') / 'test.db'
    seed_database(str(db_path))
    app = create_app({
        'TESTING': True,
        'DATABASE': str(db_path),
        'SECRET_KEY': 'test-only-secret-key',
    })
    return app


@pytest.fixture
def client(seeded_app):
    with seeded_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Helper: fetch brand/category IDs from the app's DB
# ---------------------------------------------------------------------------
def _get_ids(seeded_app, brand_name, category_name):
    with seeded_app.app_context():
        from app.db import get_db
        db = get_db()
        brand = db.execute(
            "SELECT id FROM brands WHERE name = ?", (brand_name,)
        ).fetchone()
        cat = db.execute(
            "SELECT id FROM categories WHERE name = ?", (category_name,)
        ).fetchone()
        return brand['id'], cat['id']


def _set_size_availability(seeded_app, brand_name, category_name, statuses):
    with seeded_app.app_context():
        from app.db import get_db
        db = get_db()
        brand_id, category_id = _get_ids(seeded_app, brand_name, category_name)
        chart = db.execute(
            "SELECT id FROM size_charts WHERE brand_id = ? AND category_id = ?",
            (brand_id, category_id),
        ).fetchone()
        db.executemany(
            """INSERT INTO size_availability (chart_id, size_label, in_stock)
               VALUES (?, ?, ?)
               ON CONFLICT(chart_id, size_label) DO UPDATE SET
                 in_stock = excluded.in_stock""",
            [(chart['id'], label, int(in_stock)) for label, in_stock in statuses.items()],
        )
        db.commit()
        return chart['id']


def _clear_size_availability(seeded_app, chart_id):
    with seeded_app.app_context():
        from app.db import get_db
        db = get_db()
        db.execute("DELETE FROM size_availability WHERE chart_id = ?", (chart_id,))
        db.commit()


def _csrf_token(client, path='/'):
    response = client.get(path)
    match = re.search(
        r'name="csrf_token" value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match, f'No CSRF token found on {path}'
    return match.group(1)


def _post_with_csrf(client, path, data, **kwargs):
    payload = dict(data)
    payload['csrf_token'] = _csrf_token(client, '/find-size')
    return client.post(path, data=payload, **kwargs)


def _register(client):
    email = f'{uuid.uuid4().hex}@example.test'
    response = _post_with_csrf(
        client,
        '/register',
        {'email': email, 'password': 'correct-horse-42'},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return email


# ===========================================================================
# Homepage
# ===========================================================================

def test_homepage_loads(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'SizeLens' in r.data


def test_measurement_guide_loads(client):
    r = client.get('/guide')
    assert r.status_code == 200
    html = r.data.decode()
    for measurement in ('Height', 'Chest', 'Shoulder', 'Waist', 'Hip', 'Inseam'):
        assert measurement in html


# ===========================================================================
# GET /find-size
# ===========================================================================

class TestFindSizeGet:
    def test_status_200(self, client):
        r = client.get('/find-size')
        assert r.status_code == 200

    def test_contains_brand_options(self, client):
        r = client.get('/find-size')
        html = r.data.decode()
        assert 'UrbanThread' in html
        assert 'NorthLoom' in html
        assert 'PrimeWeave' in html

    def test_contains_category_options(self, client):
        r = client.get('/find-size')
        html = r.data.decode()
        assert 'T-shirt' in html
        assert 'Jeans' in html

    def test_contains_fit_preference_radios(self, client):
        r = client.get('/find-size')
        html = r.data.decode()
        assert 'slim' in html
        assert 'regular' in html
        assert 'loose' in html

    def test_contains_measurement_fields(self, client):
        r = client.get('/find-size')
        html = r.data.decode()
        for field in ('chest', 'shoulder', 'waist', 'hip', 'inseam'):
            assert f'name="{field}"' in html

    def test_height_field_present(self, client):
        r = client.get('/find-size')
        assert b'name="height"' in r.data


# ===========================================================================
# POST /find-size – validation errors
# ===========================================================================

class TestFindSizeValidation:
    def _post(self, client, data):
        return _post_with_csrf(
            client, '/find-size', data, follow_redirects=False
        )

    def test_missing_brand_returns_400(self, client, seeded_app):
        _, cat_id = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = self._post(client, {
            'brand_id': '',
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            'chest': '90', 'shoulder': '40', 'waist': '74',
        })
        assert r.status_code == 400
        assert b'brand' in r.data.lower()

    def test_missing_category_returns_400(self, client, seeded_app):
        brand_id, _ = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': '',
            'fit_pref': 'regular',
            'chest': '90', 'shoulder': '40', 'waist': '74',
        })
        assert r.status_code == 400
        assert b'category' in r.data.lower()

    def test_missing_required_measurement_returns_400(self, client, seeded_app):
        brand_id, cat_id = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            # chest is missing
            'shoulder': '40', 'waist': '74',
        })
        assert r.status_code == 400
        assert b'Chest' in r.data

    def test_non_numeric_measurement_returns_400(self, client, seeded_app):
        brand_id, cat_id = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            'chest': 'abc', 'shoulder': '40', 'waist': '74',
        })
        assert r.status_code == 400
        assert b'number' in r.data.lower()

    def test_out_of_range_measurement_returns_400(self, client, seeded_app):
        brand_id, cat_id = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            'chest': '5',   # below 50 cm minimum
            'shoulder': '40', 'waist': '74',
        })
        assert r.status_code == 400
        assert b'50' in r.data   # mentions the minimum

    def test_valid_tshirt_post_redirects_to_result(self, client, seeded_app):
        brand_id, cat_id = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            'chest': '90', 'shoulder': '40', 'waist': '74',
        })
        assert r.status_code == 302
        assert '/result' in r.headers['Location']

    def test_valid_jeans_post_redirects_to_result(self, client, seeded_app):
        brand_id, cat_id = _get_ids(seeded_app, 'UrbanThread', 'Jeans')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            'waist': '74', 'hip': '95', 'inseam': '81',
        })
        assert r.status_code == 302
        assert '/result' in r.headers['Location']

    def test_jeans_does_not_require_chest(self, client, seeded_app):
        """Jeans only needs waist/hip/inseam; missing chest should not error."""
        brand_id, cat_id = _get_ids(seeded_app, 'UrbanThread', 'Jeans')
        r = self._post(client, {
            'brand_id': str(brand_id),
            'category_id': str(cat_id),
            'fit_pref': 'regular',
            # no chest/shoulder supplied at all
            'waist': '74', 'hip': '95', 'inseam': '81',
        })
        assert r.status_code == 302


# ===========================================================================
# GET /result – direct URL with query params
# ===========================================================================

class TestResultRoute:
    def _result(self, client, seeded_app, brand_name, cat_name, fit_pref, **measurements):
        brand_id, cat_id = _get_ids(seeded_app, brand_name, cat_name)
        params = {
            'brand_id': brand_id,
            'category_id': cat_id,
            'fit_pref': fit_pref,
            **measurements,
        }
        return client.get('/result', query_string=params)

    # -- Test case 1 from PROJECT.md: same body, different brands --

    def test_urbanthread_tshirt_regular_recommends_M(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        assert r.status_code == 200
        assert b'<strong>M</strong>' in r.data

    def test_northloom_tshirt_regular_recommends_S(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'NorthLoom', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        assert r.status_code == 200
        assert b'<strong>S</strong>' in r.data

    def test_primeweave_tshirt_regular_recommends_S(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'PrimeWeave', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        assert r.status_code == 200
        assert b'<strong>S</strong>' in r.data

    # -- Test case 2: fit preference --

    def test_northloom_loose_recommends_M(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'NorthLoom', 'T-shirt', 'loose',
            chest=92, shoulder=41, waist=77
        )
        assert r.status_code == 200
        assert b'<strong>M</strong>' in r.data

    # -- No-match --

    def test_no_match_chest_130(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=130, shoulder=40, waist=74
        )
        assert r.status_code == 200
        assert b'No good match' in r.data
        assert b'Closest chart size' in r.data
        assert b'Measurement breakdown' in r.data

    # -- Response structure tests --

    def test_result_shows_runner_up(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        assert b'Runner-up' in r.data

    def test_result_shows_scores_table(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        assert b'Scores' in r.data

    def test_result_shows_breakdown_table(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        assert b'Measurement breakdown' in r.data

    def test_result_explains_measurement_against_chart_range(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        html = r.data.decode()
        assert "Your chest (90.0 cm) is within M's range 88.0" in html

    def test_out_of_stock_best_size_shows_next_closest_available_size(
        self, client, seeded_app
    ):
        chart_id = _set_size_availability(
            seeded_app, 'UrbanThread', 'T-shirt', {'M': False}
        )
        try:
            response = self._result(
                client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
                chest=90, shoulder=40, waist=74
            )
            html = response.get_data(as_text=True)
            assert response.status_code == 200
            assert '<strong>M</strong>' in html
            assert 'Size M is out of stock.' in html
            assert 'Closest available alternative: <strong>S</strong>' in html
        finally:
            _clear_size_availability(seeded_app, chart_id)

    def test_out_of_stock_alternative_skips_other_unavailable_sizes(
        self, client, seeded_app
    ):
        chart_id = _set_size_availability(
            seeded_app,
            'UrbanThread',
            'T-shirt',
            {'M': False, 'S': False},
        )
        try:
            response = self._result(
                client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
                chest=90, shoulder=40, waist=74
            )
            html = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Closest available alternative: <strong>L</strong>' in html
        finally:
            _clear_size_availability(seeded_app, chart_id)

    def test_result_shows_confidence(self, client, seeded_app):
        r = self._result(
            client, seeded_app, 'UrbanThread', 'T-shirt', 'regular',
            chest=90, shoulder=40, waist=74
        )
        html = r.data.decode()
        assert any(c in html for c in ('high', 'medium', 'low'))

    def test_result_missing_params_returns_400(self, client):
        r = client.get('/result')
        assert r.status_code == 400

    def test_result_bad_brand_id_returns_404(self, client, seeded_app):
        _, cat_id = _get_ids(seeded_app, 'UrbanThread', 'T-shirt')
        r = client.get('/result', query_string={
            'brand_id': 9999,
            'category_id': cat_id,
            'fit_pref': 'regular',
            'chest': 90, 'shoulder': 40, 'waist': 74,
        })
        assert r.status_code == 404

    def test_jeans_result_uses_jeans_measurements(self, client, seeded_app):
        """Jeans result should show waist/hip/inseam in breakdown, not chest."""
        r = self._result(
            client, seeded_app, 'UrbanThread', 'Jeans', 'regular',
            waist=74, hip=95, inseam=81
        )
        assert r.status_code == 200
        html = r.data.decode()
        assert 'Waist' in html or 'waist' in html
        # chest should not appear in the breakdown table for jeans
        assert 'Chest' not in html
