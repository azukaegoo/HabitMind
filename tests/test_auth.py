import pytest
from app.models import User
from app import db

def test_user_registration(client, app):
    """Verify that a new user is redirected to login after registration."""
    response = client.post('/register', data={
        'email': 'new_onboarding_user@test.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers['Location']

def test_new_user_login_redirects_to_goals(client, app):
    """Verify that a user who hasn't done onboarding is redirected to goals."""
    with app.app_context():
        test_user = User(email="new_login_test@test.com", selected_goals=None) 
        test_user.set_password("password123")
        db.session.add(test_user)
        db.session.commit()

    response = client.post('/login', data={
        'email': 'new_login_test@test.com',
        'password': 'password123'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/goals" in response.headers['Location']

def test_existing_user_login_redirects_to_dashboard(client, app):
    """Verify that a user who has completed onboarding goes to dashboard."""
    with app.app_context():
        test_user = User(email="existing_user@test.com", selected_goals="sleep,stress") 
        test_user.set_password("password123")
        db.session.add(test_user)
        db.session.commit()

    response = client.post('/login', data={
        'email': 'existing_user@test.com',
        'password': 'password123'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/dashboard" in response.headers['Location']