"""
app/routes.py

Routes:
  GET  /                      – homepage
  GET  /find-size             – measurement + brand/category form
  POST /find-size             – validate inputs, redirect to /result
  GET  /result                – load chart from DB, call recommend(), render result
  GET  /profile               – placeholder
"""

from flask import (
    Blueprint, abort, g, redirect, render_template, request, session, url_for
)
from functools import wraps
import hmac
import secrets
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import get_db
from app.recommend import recommend as _recommend

bp = Blueprint('main', __name__)

# ---------------------------------------------------------------------------
# Validation ranges for each body measurement (all in cm)
# ---------------------------------------------------------------------------
MEASUREMENT_RANGES = {
    'height':   (50.0,  250.0),
    'chest':    (50.0,  200.0),
    'shoulder': (20.0,   80.0),
    'waist':    (40.0,  200.0),
    'hip':      (50.0,  200.0),
    'inseam':   (20.0,  120.0),
}

# Human-readable labels for error messages
MEASUREMENT_LABELS = {
    'height':   'Height',
    'chest':    'Chest',
    'shoulder': 'Shoulder',
    'waist':    'Waist',
    'hip':      'Hip',
    'inseam':   'Inseam',
}


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if g.user is None:
            session.clear()

    if request.method == 'POST':
        token = session.get('csrf_token')
        submitted_token = request.form.get('csrf_token', '')
        if not token or not hmac.compare_digest(token, submitted_token):
            abort(400, description='Invalid or missing CSRF token.')


@bp.app_context_processor
def inject_template_helpers():
    def csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']

    return {'csrf_token': csrf_token}


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('main.login'))
        return view(**kwargs)

    return wrapped_view


def _get_brands():
    db = get_db()
    return db.execute("SELECT id, name FROM brands ORDER BY name").fetchall()


def _get_categories():
    db = get_db()
    return db.execute("SELECT id, name FROM categories ORDER BY name").fetchall()


def _get_category_measurements(category_id: int) -> list[str]:
    """Return measurement names required by this category (from category_weights)."""
    db = get_db()
    rows = db.execute(
        "SELECT measurement FROM category_weights WHERE category_id = ? ORDER BY measurement",
        (category_id,)
    ).fetchall()
    return [r['measurement'] for r in rows]


def _validate_form(form, required_measurements: list[str]) -> tuple[dict, list[str]]:
    """
    Parse and validate the POSTed measurement form.

    Returns (values_dict, errors_list).
    values_dict maps measurement name -> float (None if field absent/optional).
    """
    values = {}
    errors = []

    for name in MEASUREMENT_RANGES:
        raw = form.get(name, '').strip()
        if not raw:
            if name in required_measurements:
                errors.append(f"{MEASUREMENT_LABELS.get(name, name)} is required.")
            values[name] = None
            continue
        try:
            val = float(raw)
        except ValueError:
            errors.append(
                f"{MEASUREMENT_LABELS.get(name, name)} must be a number."
            )
            values[name] = None
            continue
        lo, hi = MEASUREMENT_RANGES.get(name, (0, 9999))
        if not (lo <= val <= hi):
            errors.append(
                f"{MEASUREMENT_LABELS.get(name, name)} must be between "
                f"{lo:.0f} and {hi:.0f} cm."
            )
            values[name] = None
        else:
            values[name] = val

    return values, errors


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user is not None:
        return redirect(url_for('main.find_size'))

    errors = []
    email = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if len(email) > 254 or '@' not in email or '.' not in email.rsplit('@', 1)[-1]:
            errors.append('Enter a valid email address.')
        if len(password) < 8 or len(password) > 128:
            errors.append('Password must be between 8 and 128 characters.')

        if not errors:
            db = get_db()
            try:
                cursor = db.execute(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                    (email, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                errors.append('An account with that email already exists.')
            else:
                session.clear()
                session['user_id'] = cursor.lastrowid
                return redirect(url_for('main.find_size'))

    return render_template('register.html', errors=errors, email=email)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None:
        return redirect(url_for('main.find_size'))

    errors = []
    email = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = get_db().execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            errors.append('Email or password is incorrect.')
        else:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('main.find_size'))

    return render_template('login.html', errors=errors, email=email)


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('main.index'))


@bp.route('/find-size', methods=['GET', 'POST'])
def find_size():
    brands = _get_brands()
    categories = _get_categories()

    # Build category→measurements mapping for the template (drives dynamic form)
    db = get_db()
    cat_measurements = {}
    for cat in categories:
        rows = db.execute(
            "SELECT measurement FROM category_weights WHERE category_id = ?",
            (cat['id'],)
        ).fetchall()
        cat_measurements[cat['id']] = [r['measurement'] for r in rows]

    if request.method == 'GET':
        profile = {}
        if g.user is not None:
            row = db.execute(
                "SELECT height, chest, shoulder, waist, hip, inseam "
                "FROM profiles WHERE user_id = ?",
                (g.user['id'],),
            ).fetchone()
            if row:
                profile = dict(row)
        return render_template(
            'find_size.html',
            brands=brands,
            categories=categories,
            cat_measurements=cat_measurements,
            errors=[],
            form=profile,
        )

    # ---- POST: validate ----
    brand_id = request.form.get('brand_id', '').strip()
    category_id = request.form.get('category_id', '').strip()
    fit_pref = request.form.get('fit_pref', 'regular').strip()
    errors = []

    if not brand_id or not brand_id.isdigit():
        errors.append("Please select a brand.")
        brand_id_int = None
    else:
        brand_id_int = int(brand_id)

    if not category_id or not category_id.isdigit():
        errors.append("Please select a category.")
        category_id_int = None
    else:
        category_id_int = int(category_id)

    if fit_pref not in ('slim', 'regular', 'loose'):
        fit_pref = 'regular'

    required_measurements = []
    if category_id_int is not None:
        required_measurements = _get_category_measurements(category_id_int)

    values, m_errors = _validate_form(request.form, required_measurements)
    errors.extend(m_errors)

    if errors:
        return render_template(
            'find_size.html',
            brands=brands,
            categories=categories,
            cat_measurements=cat_measurements,
            errors=errors,
            form=request.form,
        ), 400

    if g.user is not None and request.form.get('save_profile') == 'on':
        db.execute(
            """INSERT INTO profiles
               (user_id, height, chest, shoulder, waist, hip, inseam)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 height = excluded.height,
                 chest = excluded.chest,
                 shoulder = excluded.shoulder,
                 waist = excluded.waist,
                 hip = excluded.hip,
                 inseam = excluded.inseam""",
            (
                g.user['id'], values['height'], values['chest'],
                values['shoulder'], values['waist'], values['hip'],
                values['inseam'],
            ),
        )
        db.commit()

    # Build query string for redirect
    params = {
        'brand_id': brand_id_int,
        'category_id': category_id_int,
        'fit_pref': fit_pref,
    }
    for m in required_measurements:
        if values.get(m) is not None:
            params[m] = values[m]
    if values.get('height') is not None:
        params['height'] = values['height']

    return redirect(url_for('main.result', **params))


@bp.route('/result')
def result():
    db = get_db()
    args = request.args

    # ---- Parse parameters ----
    try:
        brand_id = int(args['brand_id'])
        category_id = int(args['category_id'])
    except (KeyError, ValueError):
        return render_template('result.html', error="Invalid request parameters."), 400

    fit_pref = args.get('fit_pref', 'regular')
    if fit_pref not in ('slim', 'regular', 'loose'):
        fit_pref = 'regular'

    # ---- Load brand and category names ----
    brand_row = db.execute("SELECT name FROM brands WHERE id = ?", (brand_id,)).fetchone()
    category_row = db.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not brand_row or not category_row:
        return render_template('result.html', error="Brand or category not found."), 404

    # ---- Load size chart ----
    chart_row = db.execute(
        "SELECT id, chart_type FROM size_charts WHERE brand_id = ? AND category_id = ?",
        (brand_id, category_id)
    ).fetchone()
    if not chart_row:
        return render_template(
            'result.html',
            error=f"{brand_row['name']} does not have a {category_row['name']} size chart."
        ), 404

    chart_id = chart_row['id']
    chart_type = chart_row['chart_type']

    # ---- Load size rows ----
    size_rows = db.execute(
        """SELECT size_label, measurement, min_cm, max_cm
           FROM size_rows WHERE chart_id = ?
           ORDER BY id""",
        (chart_id,)
    ).fetchall()
    rows_list = [dict(r) for r in size_rows]

    # ---- Load weights for this category ----
    weight_rows = db.execute(
        "SELECT measurement, weight, ease_cm FROM category_weights WHERE category_id = ?",
        (category_id,)
    ).fetchall()
    weights_list = [dict(r) for r in weight_rows]
    known_measurements = {w['measurement'] for w in weights_list}

    # ---- Parse measurement values from query string ----
    measurements = {}
    for m in known_measurements:
        raw = args.get(m, '').strip()
        if raw:
            try:
                measurements[m] = float(raw)
            except ValueError:
                pass

    if not measurements:
        return render_template('result.html', error="No measurements provided."), 400

    # ---- Call the recommendation engine ----
    rec = _recommend(
        measurements=measurements,
        rows=rows_list,
        weights=weights_list,
        chart_type=chart_type,
        fit_pref=fit_pref,
    )
    availability_rows = db.execute(
        "SELECT size_label, in_stock FROM size_availability WHERE chart_id = ?",
        (chart_id,),
    ).fetchall()
    availability = {
        row['size_label']: bool(row['in_stock'])
        for row in availability_rows
    }
    out_of_stock_size = None
    alternative_size = None
    if rec['best_size'] is not None and not availability.get(rec['best_size'], True):
        out_of_stock_size = rec['best_size']
        available_by_score = sorted(
            rec['scores'],
            key=lambda label: rec['scores'][label],
        )
        alternative_size = next(
            (
                label for label in available_by_score
                if label != out_of_stock_size and availability.get(label, True)
            ),
            None,
        )

    if g.user is not None and rec['best_size'] is not None:
        db.execute(
            """INSERT INTO recommendations
               (user_id, chart_id, size_label, score, fit_pref)
               VALUES (?, ?, ?, ?, ?)""",
            (
                g.user['id'], chart_id, rec['best_size'],
                rec['scores'][rec['best_size']], fit_pref,
            ),
        )
        db.commit()

    closest_size = (
        min(rec['scores'], key=rec['scores'].get)
        if rec['no_match'] and rec['scores']
        else None
    )
    display_ease = {
        weight['measurement']: weight['ease_cm'] if chart_type == 'garment' else 0
        for weight in weights_list
    }

    return render_template(
        'result.html',
        brand=brand_row['name'],
        category=category_row['name'],
        chart_type=chart_type,
        fit_pref=fit_pref,
        measurements=measurements,
        rec=rec,
        closest_size=closest_size,
        display_ease=display_ease,
        out_of_stock_size=out_of_stock_size,
        alternative_size=alternative_size,
    )


@bp.route('/guide')
def guide():
    return render_template('guide.html')


@bp.route('/profile')
@login_required
def profile():
    db = get_db()
    profile_row = db.execute(
        "SELECT height, chest, shoulder, waist, hip, inseam "
        "FROM profiles WHERE user_id = ?",
        (g.user['id'],),
    ).fetchone()
    return render_template(
        'profile.html',
        profile=dict(profile_row) if profile_row else None,
    )


@bp.route('/history')
@login_required
def history():
    entries = get_db().execute(
        """SELECT r.size_label, r.score, r.fit_pref,
                  CAST(r.created_at AS TEXT) AS created_at,
                  b.name AS brand, c.name AS category
           FROM recommendations r
           JOIN size_charts sc ON sc.id = r.chart_id
           JOIN brands b ON b.id = sc.brand_id
           JOIN categories c ON c.id = sc.category_id
           WHERE r.user_id = ?
           ORDER BY r.created_at DESC, r.id DESC""",
        (g.user['id'],),
    ).fetchall()
    return render_template('history.html', entries=entries)


@bp.route('/delete-data', methods=['POST'])
@login_required
def delete_data():
    db = get_db()
    user_id = g.user['id']
    db.execute("DELETE FROM recommendations WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    session.clear()
    return redirect(url_for('main.index'))
