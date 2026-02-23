"""
Tests for Project API endpoints.

Demonstrates:
    - Proper test structure with setup/teardown
    - Testing CRUD operations end-to-end
    - Testing error cases (duplicates, not found)
    - Using TestClient for fast, isolated API testing
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.models.database import Base, engine, SessionLocal


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


class TestProjectCRUD:
    """Test project create, read, update, delete operations."""

    def test_create_project(self):
        response = client.post("/api/v1/projects", json={
            "job_number": "TEST-001",
            "name": "Test Project",
            "description": "A test project",
            "current_stage": "0 - Strategic Definition",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["job_number"] == "TEST-001"
        assert data["name"] == "Test Project"
        assert data["is_active"] is True

    def test_duplicate_job_number_rejected(self):
        """Ensure duplicate job numbers are caught."""
        client.post("/api/v1/projects", json={
            "job_number": "TEST-DUP",
            "name": "First Project",
        })
        response = client.post("/api/v1/projects", json={
            "job_number": "TEST-DUP",
            "name": "Duplicate Project",
        })
        assert response.status_code == 409

    def test_list_projects(self):
        client.post("/api/v1/projects", json={
            "job_number": "LIST-001",
            "name": "Project One",
        })
        client.post("/api/v1/projects", json={
            "job_number": "LIST-002",
            "name": "Project Two",
        })
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        assert len(response.json()) >= 2

    def test_get_single_project(self):
        create_resp = client.post("/api/v1/projects", json={
            "job_number": "GET-001",
            "name": "Single Project",
        })
        project_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Single Project"

    def test_get_nonexistent_project(self):
        response = client.get("/api/v1/projects/99999")
        assert response.status_code == 404

    def test_update_project(self):
        create_resp = client.post("/api/v1/projects", json={
            "job_number": "UPD-001",
            "name": "Before Update",
        })
        project_id = create_resp.json()["id"]

        response = client.patch(f"/api/v1/projects/{project_id}", json={
            "name": "After Update",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "After Update"

    def test_soft_delete_project(self):
        create_resp = client.post("/api/v1/projects", json={
            "job_number": "DEL-001",
            "name": "To Be Deleted",
        })
        project_id = create_resp.json()["id"]

        # Delete
        del_resp = client.delete(f"/api/v1/projects/{project_id}")
        assert del_resp.status_code == 200

        # Should no longer appear in list
        list_resp = client.get("/api/v1/projects")
        project_ids = [p["id"] for p in list_resp.json()]
        assert project_id not in project_ids

    def test_filter_by_status(self):
        response = client.get("/api/v1/projects?status=Invalid")
        assert response.status_code == 400
