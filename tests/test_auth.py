import pytest
from app.models import User
from app import db

def test_user_registration(client, app):
    """Verify that a new user can register successfully."""
    response = client.post('/register', data={
        'email': 'new_user@test.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

def test_user_login(client, app):
    """Verify that an existing user can log in."""
    with app.app_context():
        test_user = User(email="login_test@test.com")
        test_user.set_password("password123")
        db.session.add(test_user)
        db.session.commit()
    response = client.post('/login', data={'email': 'login_test@test.com', 'password': 'password123'}, follow_redirects=True)
    assert response.status_code == 200