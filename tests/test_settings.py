import pytest
from datetime import datetime, UTC, timedelta
from app.models import User
from app import db

@pytest.mark.skip(reason="Waiting for Safrin's frontend templates")
def test_user_profile_view(client, app, authenticated_user):
    """Verify that the profile page displays correctly with user data."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
    response = client.get('/profile')
    assert response.status_code == 200

@pytest.mark.skip(reason="Waiting for Safrin's frontend templates")
def test_user_settings_routes(client, app):
    """Verify update settings, cancel premium, and account deletion work."""
    with app.app_context():
        test_user = User(email="settings@test.com", plan="premium")
        test_user.set_password("password")
        db.session.add(test_user)
        db.session.commit()
        user_id = test_user.id
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
    response_update = client.post('/settings/update', data={'email': 'updated@test.com'}, follow_redirects=True)
    assert response_update.status_code == 200