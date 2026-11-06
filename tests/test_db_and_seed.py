import sqlite3
import pytest
from seed import seed_database

def test_seed_database_in_temp_file(tmp_path):
    db_file = tmp_path / "test_sizelens.db"
    summary = seed_database(str(db_file))

    assert summary['brands'] == 3
    assert summary['categories'] == 2
    assert summary['category_weights'] == 6
    assert summary['size_charts'] == 6
    assert summary['size_rows'] == 72
    assert summary['total'] == 89

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    # Verify brands
    brands = [r['name'] for r in conn.execute("SELECT name FROM brands ORDER BY name").fetchall()]
    assert brands == ['NorthLoom', 'PrimeWeave', 'UrbanThread']

    # Verify categories
    categories = [r['name'] for r in conn.execute("SELECT name FROM categories ORDER BY name").fetchall()]
    assert categories == ['Jeans', 'T-shirt']

    # Verify chart types
    chart_info = conn.execute("""
        SELECT b.name as brand, c.name as category, sc.chart_type
        FROM size_charts sc
        JOIN brands b ON sc.brand_id = b.id
        JOIN categories c ON sc.category_id = c.id
    """).fetchall()

    chart_dict = {(r['brand'], r['category']): r['chart_type'] for r in chart_info}
    assert chart_dict[('UrbanThread', 'T-shirt')] == 'body'
    assert chart_dict[('UrbanThread', 'Jeans')] == 'body'
    assert chart_dict[('NorthLoom', 'T-shirt')] == 'body'
    assert chart_dict[('NorthLoom', 'Jeans')] == 'body'
    assert chart_dict[('PrimeWeave', 'T-shirt')] == 'garment'
    assert chart_dict[('PrimeWeave', 'Jeans')] == 'garment'

    # Verify T-shirt category weights and ease
    weights_info = conn.execute("""
        SELECT cw.measurement, cw.weight, cw.ease_cm
        FROM category_weights cw
        JOIN categories c ON cw.category_id = c.id
        WHERE c.name = 'T-shirt'
    """).fetchall()
    tshirt_weights = {r['measurement']: (r['weight'], r['ease_cm']) for r in weights_info}
    assert tshirt_weights['chest'] == (0.40, 10.0)
    assert tshirt_weights['shoulder'] == (0.35, 1.0)
    assert tshirt_weights['waist'] == (0.25, 10.0)

    # Verify Jeans category weights and ease (no ease)
    jeans_weights_info = conn.execute("""
        SELECT cw.measurement, cw.weight, cw.ease_cm
        FROM category_weights cw
        JOIN categories c ON cw.category_id = c.id
        WHERE c.name = 'Jeans'
    """).fetchall()
    jeans_weights = {r['measurement']: (r['weight'], r['ease_cm']) for r in jeans_weights_info}
    assert jeans_weights['waist'] == (0.50, 0.0)
    assert jeans_weights['hip'] == (0.30, 0.0)
    assert jeans_weights['inseam'] == (0.20, 0.0)

    # Check UrbanThread T-shirt size M
    ut_m_rows = conn.execute("""
        SELECT sr.measurement, sr.min_cm, sr.max_cm
        FROM size_rows sr
        JOIN size_charts sc ON sr.chart_id = sc.id
        JOIN brands b ON sc.brand_id = b.id
        JOIN categories c ON sc.category_id = c.id
        WHERE b.name = 'UrbanThread' AND c.name = 'T-shirt' AND sr.size_label = 'M'
    """).fetchall()
    ut_m = {r['measurement']: (r['min_cm'], r['max_cm']) for r in ut_m_rows}
    assert ut_m['chest'] == (88.0, 93.0)
    assert ut_m['shoulder'] == (40.0, 42.0)
    assert ut_m['waist'] == (74.0, 79.0)

    conn.close()


def test_if_empty_seed_preserves_existing_users_and_size_data(tmp_path):
    db_file = tmp_path / "nested" / "data" / "sizelens.db"
    seed_database(str(db_file))

    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("preserve@example.test", "test-hash"),
    )
    conn.commit()
    conn.close()

    summary = seed_database(str(db_file), reset=False)
    assert summary['brands'] == 3

    conn = sqlite3.connect(str(db_file))
    user_count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE email = ?",
        ("preserve@example.test",),
    ).fetchone()[0]
    brand_count = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    conn.close()

    assert user_count == 1
    assert brand_count == 3
