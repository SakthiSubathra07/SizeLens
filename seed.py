import sqlite3
import os
import argparse
from app import config
from app.db import init_db

DROP_TABLES_SQL = """
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS profiles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS category_weights;
DROP TABLE IF EXISTS size_availability;
DROP TABLE IF EXISTS size_rows;
DROP TABLE IF EXISTS size_charts;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS brands;
PRAGMA foreign_keys = ON;
"""

def seed_database(db_path=None, reset=True):
    """Drop and recreate the database, seeding it with brand charts and weights."""
    if db_path is None:
        db_path = config.DATABASE

    database_dir = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(database_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    if not reset:
        init_db(conn)
        seeded_brands = cursor.execute(
            "SELECT COUNT(*) FROM brands"
        ).fetchone()[0]
        if seeded_brands:
            summary = {
                'brands': cursor.execute("SELECT COUNT(*) FROM brands").fetchone()[0],
                'categories': cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0],
                'category_weights': cursor.execute("SELECT COUNT(*) FROM category_weights").fetchone()[0],
                'size_charts': cursor.execute("SELECT COUNT(*) FROM size_charts").fetchone()[0],
                'size_rows': cursor.execute("SELECT COUNT(*) FROM size_rows").fetchone()[0],
            }
            summary['total'] = sum(summary.values())
            conn.close()
            print("Existing size data found; preserving the database.")
            return summary
        existing_data = sum(
            cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                'categories', 'category_weights', 'size_charts', 'size_rows',
                'size_availability', 'users', 'profiles', 'recommendations',
            )
        )
        if existing_data:
            conn.close()
            raise RuntimeError(
                'Database has existing records but no brands; refusing to '
                'reset potentially valuable data.'
            )

    # Drop existing tables
    cursor.executescript(DROP_TABLES_SQL)

    # Recreate tables from schema
    init_db(conn)

    # 1. Brands
    brands = [
        ('UrbanThread',),
        ('NorthLoom',),
        ('PrimeWeave',)
    ]
    cursor.executemany("INSERT INTO brands (name) VALUES (?)", brands)
    brand_map = {row['name']: row['id'] for row in cursor.execute("SELECT id, name FROM brands").fetchall()}

    # 2. Categories
    categories = [
        ('T-shirt',),
        ('Jeans',)
    ]
    cursor.executemany("INSERT INTO categories (name) VALUES (?)", categories)
    cat_map = {row['name']: row['id'] for row in cursor.execute("SELECT id, name FROM categories").fetchall()}

    # 3. Category Weights
    # T-shirt: chest 0.40, shoulder 0.35, waist 0.25. Ease: chest 10, shoulder 1, waist 10
    # Jeans: waist 0.50, hip 0.30, inseam 0.20. No ease (0)
    category_weights = [
        # T-shirt
        (cat_map['T-shirt'], 'chest', 0.40, 10.0),
        (cat_map['T-shirt'], 'shoulder', 0.35, 1.0),
        (cat_map['T-shirt'], 'waist', 0.25, 10.0),
        # Jeans
        (cat_map['Jeans'], 'waist', 0.50, 0.0),
        (cat_map['Jeans'], 'hip', 0.30, 0.0),
        (cat_map['Jeans'], 'inseam', 0.20, 0.0),
    ]
    cursor.executemany(
        "INSERT INTO category_weights (category_id, measurement, weight, ease_cm) VALUES (?, ?, ?, ?)",
        category_weights
    )

    # 4. Size Charts
    # Brand body vs garment types:
    # UrbanThread: body
    # NorthLoom: body
    # PrimeWeave: garment
    charts = [
        (brand_map['UrbanThread'], cat_map['T-shirt'], 'body', 'UrbanThread body size chart for T-shirts'),
        (brand_map['UrbanThread'], cat_map['Jeans'], 'body', 'UrbanThread body size chart for Jeans'),
        (brand_map['NorthLoom'], cat_map['T-shirt'], 'body', 'NorthLoom body size chart for T-shirts'),
        (brand_map['NorthLoom'], cat_map['Jeans'], 'body', 'NorthLoom body size chart for Jeans'),
        (brand_map['PrimeWeave'], cat_map['T-shirt'], 'garment', 'PrimeWeave garment size chart for T-shirts'),
        (brand_map['PrimeWeave'], cat_map['Jeans'], 'garment', 'PrimeWeave garment size chart for Jeans'),
    ]
    cursor.executemany(
        "INSERT INTO size_charts (brand_id, category_id, chart_type, notes) VALUES (?, ?, ?, ?)",
        charts
    )

    # Fetch chart IDs
    chart_rows = cursor.execute("SELECT id, brand_id, category_id FROM size_charts").fetchall()
    chart_map = {(row['brand_id'], row['category_id']): row['id'] for row in chart_rows}

    # 5. Size Rows
    size_rows_data = []

    # --- T-SHIRT DATA ---
    # UrbanThread (body chart)
    ut_tshirt_id = chart_map[(brand_map['UrbanThread'], cat_map['T-shirt'])]
    ut_tshirt = [
        ('S', [('chest', 82.0, 87.0), ('shoulder', 37.0, 39.0), ('waist', 68.0, 73.0)]),
        ('M', [('chest', 88.0, 93.0), ('shoulder', 40.0, 42.0), ('waist', 74.0, 79.0)]),
        ('L', [('chest', 94.0, 99.0), ('shoulder', 43.0, 45.0), ('waist', 80.0, 85.0)]),
        ('XL', [('chest', 100.0, 105.0), ('shoulder', 46.0, 48.0), ('waist', 86.0, 91.0)]),
    ]
    for size_label, measurements in ut_tshirt:
        for m_name, min_cm, max_cm in measurements:
            size_rows_data.append((ut_tshirt_id, size_label, m_name, min_cm, max_cm))

    # NorthLoom (body chart)
    nl_tshirt_id = chart_map[(brand_map['NorthLoom'], cat_map['T-shirt'])]
    nl_tshirt = [
        ('S', [('chest', 86.0, 91.0), ('shoulder', 39.0, 41.0), ('waist', 72.0, 77.0)]),
        ('M', [('chest', 92.0, 97.0), ('shoulder', 42.0, 44.0), ('waist', 78.0, 83.0)]),
        ('L', [('chest', 98.0, 103.0), ('shoulder', 45.0, 47.0), ('waist', 84.0, 89.0)]),
        ('XL', [('chest', 104.0, 109.0), ('shoulder', 48.0, 50.0), ('waist', 90.0, 95.0)]),
    ]
    for size_label, measurements in nl_tshirt:
        for m_name, min_cm, max_cm in measurements:
            size_rows_data.append((nl_tshirt_id, size_label, m_name, min_cm, max_cm))

    # PrimeWeave (garment chart)
    pw_tshirt_id = chart_map[(brand_map['PrimeWeave'], cat_map['T-shirt'])]
    pw_tshirt = [
        ('S', [('chest', 94.0, 99.0), ('shoulder', 40.0, 42.0), ('waist', 80.0, 85.0)]),
        ('M', [('chest', 100.0, 105.0), ('shoulder', 43.0, 45.0), ('waist', 86.0, 91.0)]),
        ('L', [('chest', 106.0, 111.0), ('shoulder', 46.0, 48.0), ('waist', 92.0, 97.0)]),
        ('XL', [('chest', 112.0, 117.0), ('shoulder', 49.0, 51.0), ('waist', 98.0, 103.0)]),
    ]
    for size_label, measurements in pw_tshirt:
        for m_name, min_cm, max_cm in measurements:
            size_rows_data.append((pw_tshirt_id, size_label, m_name, min_cm, max_cm))

    # --- JEANS DATA ---
    # UrbanThread (body chart)
    ut_jeans_id = chart_map[(brand_map['UrbanThread'], cat_map['Jeans'])]
    ut_jeans = [
        ('28', [('waist', 70.0, 73.0), ('hip', 88.0, 91.0), ('inseam', 78.0, 81.0)]),
        ('30', [('waist', 74.0, 78.0), ('hip', 92.0, 96.0), ('inseam', 80.0, 83.0)]),
        ('32', [('waist', 79.0, 83.0), ('hip', 97.0, 101.0), ('inseam', 81.0, 84.0)]),
        ('34', [('waist', 84.0, 88.0), ('hip', 102.0, 106.0), ('inseam', 82.0, 85.0)]),
    ]
    for size_label, measurements in ut_jeans:
        for m_name, min_cm, max_cm in measurements:
            size_rows_data.append((ut_jeans_id, size_label, m_name, min_cm, max_cm))

    # NorthLoom (body chart)
    nl_jeans_id = chart_map[(brand_map['NorthLoom'], cat_map['Jeans'])]
    nl_jeans = [
        ('28', [('waist', 71.0, 74.0), ('hip', 89.0, 92.0), ('inseam', 79.0, 82.0)]),
        ('30', [('waist', 75.0, 79.0), ('hip', 93.0, 97.0), ('inseam', 81.0, 84.0)]),
        ('32', [('waist', 80.0, 84.0), ('hip', 98.0, 102.0), ('inseam', 82.0, 85.0)]),
        ('34', [('waist', 85.0, 89.0), ('hip', 103.0, 107.0), ('inseam', 83.0, 86.0)]),
    ]
    for size_label, measurements in nl_jeans:
        for m_name, min_cm, max_cm in measurements:
            size_rows_data.append((nl_jeans_id, size_label, m_name, min_cm, max_cm))

    # PrimeWeave (garment chart)
    pw_jeans_id = chart_map[(brand_map['PrimeWeave'], cat_map['Jeans'])]
    pw_jeans = [
        ('28', [('waist', 72.0, 75.0), ('hip', 90.0, 93.0), ('inseam', 80.0, 83.0)]),
        ('30', [('waist', 76.0, 80.0), ('hip', 94.0, 98.0), ('inseam', 82.0, 85.0)]),
        ('32', [('waist', 81.0, 85.0), ('hip', 99.0, 103.0), ('inseam', 83.0, 86.0)]),
        ('34', [('waist', 86.0, 90.0), ('hip', 104.0, 108.0), ('inseam', 84.0, 87.0)]),
    ]
    for size_label, measurements in pw_jeans:
        for m_name, min_cm, max_cm in measurements:
            size_rows_data.append((pw_jeans_id, size_label, m_name, min_cm, max_cm))

    cursor.executemany(
        "INSERT INTO size_rows (chart_id, size_label, measurement, min_cm, max_cm) VALUES (?, ?, ?, ?, ?)",
        size_rows_data
    )

    conn.commit()

    # Query counts for summary
    brand_count = cursor.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    category_count = cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    weights_count = cursor.execute("SELECT COUNT(*) FROM category_weights").fetchone()[0]
    charts_count = cursor.execute("SELECT COUNT(*) FROM size_charts").fetchone()[0]
    rows_count = cursor.execute("SELECT COUNT(*) FROM size_rows").fetchone()[0]
    total_inserted = brand_count + category_count + weights_count + charts_count + rows_count

    conn.close()

    summary = {
        'brands': brand_count,
        'categories': category_count,
        'category_weights': weights_count,
        'size_charts': charts_count,
        'size_rows': rows_count,
        'total': total_inserted
    }

    print("=" * 45)
    print("Database dropped and recreated successfully.")
    print("Summary of rows inserted:")
    print(f"  - brands: {brand_count}")
    print(f"  - categories: {category_count}")
    print(f"  - category_weights: {weights_count}")
    print(f"  - size_charts: {charts_count}")
    print(f"  - size_rows: {rows_count}")
    print(f"Total rows inserted: {total_inserted}")
    print("=" * 45)

    return summary

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed the SizeLens database.')
    parser.add_argument(
        '--if-empty',
        action='store_true',
        help='Seed only if no brand data exists; preserve any existing data.',
    )
    arguments = parser.parse_args()
    seed_database(reset=not arguments.if_empty)
