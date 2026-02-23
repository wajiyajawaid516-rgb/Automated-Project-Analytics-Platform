"""
Tests for Contact and Directory API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.models.database import Base, engine


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


class TestContacts:
    def test_create_contact(self):
        response = client.post("/api/v1/contacts", json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
        })
        assert response.status_code == 201
        assert response.json()["first_name"] == "Test"

    def test_search_contacts(self):
        client.post("/api/v1/contacts", json={
            "first_name": "John",
            "last_name": "Smith",
        })
        response = client.get("/api/v1/contacts?search=John")
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestDirectory:
    def _create_project_and_contact(self):
        proj = client.post("/api/v1/projects", json={
            "job_number": "DIR-001",
            "name": "Directory Test Project",
        }).json()
        contact = client.post("/api/v1/contacts", json={
            "first_name": "Jane",
            "last_name": "Doe",
        }).json()
        return proj["id"], contact["id"]

    def test_add_contact_to_directory(self):
        proj_id, contact_id = self._create_project_and_contact()
        response = client.post(f"/api/v1/projects/{proj_id}/directory", json={
            "project_id": proj_id,
            "contact_id": contact_id,
            "role": "Engineer",
        })
        assert response.status_code == 201

    def test_idempotent_add(self):
        """Adding the same contact twice should not create duplicates."""
        proj_id, contact_id = self._create_project_and_contact()
        payload = {
            "project_id": proj_id,
            "contact_id": contact_id,
            "role": "Architect",
        }
        client.post(f"/api/v1/projects/{proj_id}/directory", json=payload)
        client.post(f"/api/v1/projects/{proj_id}/directory", json=payload)

        # Should still only have one entry
        dir_resp = client.get(f"/api/v1/projects/{proj_id}/directory")
        entries = dir_resp.json()
        architect_entries = [e for e in entries if e["role"] == "Architect"]
        assert len(architect_entries) == 1

    def test_remove_from_directory(self):
        proj_id, contact_id = self._create_project_and_contact()
        add_resp = client.post(f"/api/v1/projects/{proj_id}/directory", json={
            "project_id": proj_id,
            "contact_id": contact_id,
            "role": "Client",
        })
        entry_id = add_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/projects/{proj_id}/directory/{entry_id}")
        assert del_resp.status_code == 200
