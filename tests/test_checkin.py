import pytest
from datetime import datetime, UTC

# Import from the 'app' package based on your directory structure
from app import create_app, db
from app.models import User, CheckIn

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    
    # Define test configurations as a dictionary
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False  # Disable CSRF for easier testing
    }
    
    # Pass the dictionary to the factory function instead of a string
    app = create_app(test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def authenticated_user(app):
    """Create a test user and simulate an authenticated session."""
    with app.app_context():
        user = User(email="test@example.com", plan="free")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        # [FIX ADDED] Refresh to load the generated ID, then expunge (detach) it cleanly
        # so SQLAlchemy doesn't try to access the closed session later in the test.
        db.session.refresh(user)
        db.session.expunge(user)
        
        return user

def test_checkin_integration_flow(client, app, authenticated_user):
    """Test the daily check-in creation and update flow."""
    
    # Simulate user login session for Flask-Login
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True

    # ---- Step 1: Initial Check-In (POST) ----
    form_data = {
        "mood_score": "4",
        "habits": "exercise, reading",
        "note": "Studied hard today!"
    }
    
    response = client.post('/checkin', data=form_data, follow_redirects=True)
    
    # Verify successful redirect to dashboard
    assert response.status_code == 200
    
    # Verify data was inserted into the database correctly
    with app.app_context():
        today = datetime.now(UTC).date()
        checkin = CheckIn.query.filter_by(user_id=authenticated_user.id, date=today).first()
        assert checkin is not None
        assert checkin.mood_score == 4
        assert checkin.habits == "exercise, reading"

    # ---- Step 2: Update Check-In (Same Date) ----
    updated_form_data = {
        "mood_score": "5",
        "habits": "exercise, coding",
        "note": "Updated note: finished the backend logic."
    }
    
    response_update = client.post('/checkin', data=updated_form_data, follow_redirects=True)
    assert response_update.status_code == 200
    
    # Verify the database record was updated, not duplicated
    with app.app_context():
        all_checkins = CheckIn.query.filter_by(user_id=authenticated_user.id).all()
        assert len(all_checkins) == 1  # Should still be exactly 1 record due to UniqueConstraint
        
        updated_checkin = all_checkins[0]
        assert updated_checkin.mood_score == 5
        assert updated_checkin.habits == "exercise, coding"
        assert updated_checkin.note == "Updated note: finished the backend logic."