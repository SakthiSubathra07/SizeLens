import re
import uuid

import pytest
from werkzeug.security import check_password_hash

from app import create_app
from app.db import get_db
from seed import seed_database


@pytest.fixture
def account_app(tmp_path):
    database = tmp_path / 'accounts.db'
    seed_database(str(database))
    return create_app({
        'TESTING': True,
        'DATABASE': str(database),
        'SECRET_KEY': 'account-test-secret',
    })


@pytest.fixture
def client(account_app):
    with account_app.test_client() as test_client:
        yield test_client


def _token(client, path='/'):
    response = client.get(path)
    match = re.search(
        r'name="csrf_token" value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return match.group(1)


def _post(client, path, data):
    payload = dict(data)
    token_page = {
        '/register': '/register',
        '/login': '/login',
        '/logout': '/',
        '/find-size': '/find-size',
        '/delete-data': '/profile',
    }[path]
    payload['csrf_token'] = _token(client, token_page)
    return client.post(path, data=payload, follow_redirects=False)


def _register(client):
    email = f'{uuid.uuid4().hex}@example.test'
    response = _post(
        client, '/register',
        {'email': email, 'password': 'valid-test-password'},
    )
    assert response.status_code == 302
    return email


def _recommend(client):
    response = client.get(
        '/result?brand_id=1&category_id=1&fit_pref=regular'
        '&chest=90&shoulder=40&waist=74'
    )
    assert response.status_code == 200
    assert b'<strong>M</strong>' in response.data


def test_registration_stores_werkzeug_password_hash(client, account_app):
    email = f'{uuid.uuid4().hex}@example.test'
    response = _post(
        client, '/register',
        {'email': email.upper(), 'password': 'valid-test-password'},
    )
    assert response.status_code == 302

    with account_app.app_context():
        user = get_db().execute(
            "SELECT email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    assert user['email'] == email
    assert user['password_hash'] != 'valid-test-password'
    assert check_password_hash(user['password_hash'], 'valid-test-password')


def test_login_accepts_registered_credentials(client):
    email = _register(client)
    assert _post(client, '/logout', {}).status_code == 302

    response = _post(
        client, '/login',
        {'email': email, 'password': 'valid-test-password'},
    )
    assert response.status_code == 302
    assert client.get('/profile').status_code == 200


def test_post_without_csrf_token_is_rejected(client):
    response = client.post(
        '/register',
        data={'email': 'csrf@example.test', 'password': 'valid-test-password'},
    )
    assert response.status_code == 400


def test_profile_is_saved_prefilled_and_recommendation_is_listed(
    client, account_app
):
    _register(client)
    response = _post(
        client,
        '/find-size',
        {
            'brand_id': '1',
            'category_id': '1',
            'fit_pref': 'regular',
            'chest': '90',
            'shoulder': '40',
            'waist': '74',
            'height': '175',
            'save_profile': 'on',
        },
    )
    assert response.status_code == 302
    _recommend(client)

    with account_app.app_context():
        db = get_db()
        profile = db.execute(
            "SELECT chest, shoulder, waist, height FROM profiles"
        ).fetchone()
        recommendation = db.execute(
            "SELECT size_label, score FROM recommendations"
        ).fetchone()
    assert dict(profile) == {
        'chest': 90.0,
        'shoulder': 40.0,
        'waist': 74.0,
        'height': 175.0,
    }
    assert recommendation['size_label'] == 'M'
    assert recommendation['score'] == 0

    form = client.get('/find-size').get_data(as_text=True)
    assert 'value="90.0"' in form
    history = client.get('/history')
    assert history.status_code == 200
    assert b'UrbanThread' in history.data
    assert b'T-shirt' in history.data
    assert b'<strong>M</strong>' in history.data


def test_profile_saving_is_optional(client, account_app):
    _register(client)
    response = _post(
        client,
        '/find-size',
        {
            'brand_id': '1',
            'category_id': '1',
            'fit_pref': 'regular',
            'chest': '90',
            'shoulder': '40',
            'waist': '74',
        },
    )
    assert response.status_code == 302
    with account_app.app_context():
        count = get_db().execute(
            "SELECT COUNT(*) FROM profiles"
        ).fetchone()[0]
    assert count == 0


def test_delete_my_data_removes_account_profile_and_history(
    client, account_app
):
    _register(client)
    _post(
        client,
        '/find-size',
        {
            'brand_id': '1',
            'category_id': '1',
            'fit_pref': 'regular',
            'chest': '90',
            'shoulder': '40',
            'waist': '74',
            'save_profile': 'on',
        },
    )
    _recommend(client)

    response = _post(client, '/delete-data', {})
    assert response.status_code == 302
    assert client.get('/history').status_code == 302

    with account_app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM recommendations"
        ).fetchone()[0] == 0
