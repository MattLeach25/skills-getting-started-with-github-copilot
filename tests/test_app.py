"""
Tests for the Mergington High School API endpoints.

Uses the AAA (Arrange-Act-Assert) pattern:
  - Arrange: Set up test data and preconditions
  - Act: Execute the action under test
  - Assert: Verify the expected outcome
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities

# Snapshot of the original activities state for resetting between tests
_original_activities = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities database to its original state after each test."""
    yield
    for key in activities:
        activities[key]["participants"] = list(_original_activities[key]["participants"])


@pytest.fixture
def client():
    """Provide a FastAPI TestClient instance."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /  (redirect to static page)
# ---------------------------------------------------------------------------

class TestRootRedirect:
    def test_root_redirects_to_index(self, client):
        # Arrange
        url = "/"

        # Act
        response = client.get(url)

        # Assert — TestClient follows redirects, so we land on the HTML page
        assert response.status_code == 200
        assert "Mergington High School" in response.text


# ---------------------------------------------------------------------------
# GET /activities
# ---------------------------------------------------------------------------

class TestGetActivities:
    def test_returns_all_activities(self, client):
        # Arrange
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class",
            "Soccer Team", "Basketball Team", "Art Club",
            "Drama Club", "Debate Team", "Science Olympiad",
        ]

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        for name in expected_activities:
            assert name in data

    def test_activity_has_required_fields(self, client):
        # Arrange
        required_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for name, details in data.items():
            assert required_fields.issubset(details.keys()), (
                f"{name} is missing fields: {required_fields - details.keys()}"
            )

    def test_participants_is_a_list(self, client):
        # Arrange / Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for name, details in data.items():
            assert isinstance(details["participants"], list), (
                f"{name} participants should be a list"
            )


# ---------------------------------------------------------------------------
# POST /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_successful_signup(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity_name}"
        assert email in activities[activity_name]["participants"]

    def test_signup_activity_not_found(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "someone@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_duplicate_signup_is_allowed(self, client):
        """
        Documents current behavior: the API does not prevent duplicate signups.
        The same email can be added to an activity more than once.
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # already a participant
        count_before = activities[activity_name]["participants"].count(email)

        # Act
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert — email now appears one more time
        count_after = activities[activity_name]["participants"].count(email)
        assert count_after == count_before + 1


# ---------------------------------------------------------------------------
# DELETE /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

class TestUnregister:
    def test_successful_unregister(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        assert email in activities[activity_name]["participants"]

        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
        assert email not in activities[activity_name]["participants"]

    def test_unregister_activity_not_found(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "someone@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_email_not_in_activity(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "unknown@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not found in activity"
