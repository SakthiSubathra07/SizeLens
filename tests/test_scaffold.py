import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret-key'})
    with app.test_client() as client:
        yield client

def test_homepage_status(client):
    """Test that homepage loads successfully."""
    response = client.get('/')
    assert response.status_code == 200

def test_homepage_navigation(client):
    """Test that homepage contains navigation links: Home, Find my size, My profile."""
    response = client.get('/')
    html = response.get_data(as_text=True)
    assert 'Home' in html
    assert 'Find my size' in html
    assert 'My profile' in html
