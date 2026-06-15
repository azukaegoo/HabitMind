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
<<<<<<< HEAD
        # 🚨 수정된 부분: name="Test User" 를 추가했습니다!
        user = User(name="Test User", email="test@example.com", plan="free")
=======
        user = User(
            name="Test User",
            email="test@example.com",
            plan="free"
        )
>>>>>>> eef2da239fc9d99b6046eb29baeb5f81ec6e3d52
        user.set_password("password123")

        db.session.add(user)
        db.session.commit()
        
        db.session.refresh(user)
        db.session.expunge(user)
        
        return user