import pytest
from datetime import datetime, UTC, timedelta
from app.models import User, CheckIn, CurrentInsight, InsightReport
from app import db

@pytest.mark.skip(reason="Waiting for Safrin's frontend templates")
def test_checkin_get_route(client, app, authenticated_user):
    """Test the GET route for rendering the form and completed states."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
    response_initial = client.get('/checkin')
    assert response_initial.status_code == 200

def test_checkin_integration_flow(client, app, authenticated_user):
    """Test the daily check-in creation and update flow."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
    form_data = {"mood_score": "4", "habits": "exercise, reading", "note": "Studied hard today!"}
    response = client.post('/check-in', data=form_data, follow_redirects=True)
    assert response.status_code == 200

@pytest.mark.skip(reason="Waiting for Safrin's frontend templates")
def test_weekly_insight_generation_and_view(client, app, authenticated_user):
    """Verify that a weekly insight can be generated and viewed."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
    response_post = client.post('/insights/generate', follow_redirects=True)
    assert response_post.status_code == 200

def test_goals_onboarding_redirects_to_habits(client, app, authenticated_user):
    """Verify that submitting goals redirects to the habits selection step."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
        
    response = client.post('/goals', data={'goals': 'sleep,stress'}, follow_redirects=False)
    
    assert response.status_code == 302
    assert "/habits" in response.headers['Location']

def test_habits_onboarding_redirects_to_complete(client, app, authenticated_user):
    """Verify that submitting habits redirects to the completion screen."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
        
    response = client.post('/habits', data={'habits': '1,2,3,4,5'}, follow_redirects=False)
    
    assert response.status_code == 302
    assert "/complete" in response.headers['Location']