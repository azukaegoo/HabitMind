import pytest
from app import create_app, db
from app.models import User

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    }
    app = create_app(test_config)

    with app.app_context():
        # Create tables
        db.create_all()
        
        # Pre-populate the test database with a default user
        user = User(name="Test User", email="test@example.com", plan="free")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        yield app
        
        # Clean up after tests finish
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def auth(client):
    """Authentication helper to simulate real user logins/logouts."""
    class AuthActions:
        def login(self, email="test@example.com", password="password123"):
            return client.post('/login', data={
                'email': email,
                'password': password
            }, follow_redirects=True)
            
        def logout(self):
            return client.get('/logout', follow_redirects=True)
            
    return AuthActions()

@pytest.fixture
def authenticated_user(app):
    """Restore the old fixture for test_checkin.py compatibility."""
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        return user