import pytest

# ==========================================
# 1. Authentication Tests
# ==========================================
def test_login_logout(client, auth):
    """Test that a user can log in and log out successfully."""
    response = auth.login()
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Choose Your Goals' in response.data

    response = auth.logout()
    assert response.status_code == 200
    assert b'Sign In' in response.data or b'Log In' in response.data or b'HabitMind' in response.data

# ==========================================
# 2. Dashboard Route Tests
# ==========================================
def test_dashboard_requires_login(client):
    """Test that dashboard redirects to login if the user is not authenticated."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')

def test_dashboard_access(client, auth):
    """Test that the dashboard is accessible when logged in."""
    auth.login()
    response = client.get('/dashboard')
    assert response.status_code == 200

# ==========================================
# 3. Check-in Route Tests
# ==========================================
@pytest.mark.skip(reason="Waiting for frontend templates/routing from Safrin")
def test_checkin_access(client, auth):
    """Test that the check-in page is accessible when logged in."""
    auth.login()
    response = client.get('/checkin')
    assert response.status_code == 200

# ==========================================
# 4. Settings & Change Password Tests
# ==========================================
def test_settings_access(client, auth):
    """Test that the settings page loads properly."""
    auth.login()
    response = client.get('/settings')
    assert response.status_code == 200
    assert b'Change Password' in response.data

def test_change_password_failure(client, auth):
    """Test change password functionality with an incorrect current password."""
    auth.login()
    
    response = client.post('/change-password', data={
        'current_password': 'wrong_password_here',
        'new_password': 'newpassword456'
    })
    
    assert response.status_code == 302
    assert '/settings' in response.headers.get('Location', '')

def test_change_password_success(client, auth):
    """Test change password functionality with the correct current password."""
    auth.login()
    
    response = client.post('/change-password', data={
        'current_password': 'password123',
        'new_password': 'newpassword456'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Password changed successfully' in response.data