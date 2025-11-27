# tests/test_crossword.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


def test_generate_without_theme_returns_400(client):
    """Test that /generate returns 400 when theme is missing."""
    res = client.post("/crossword/generate", json={})
    assert res.status_code == 400
    assert "must include" in res.json()["detail"]


def test_generate_with_empty_theme_returns_400(client):
    """Test that /generate returns 400 when theme is empty string."""
    res = client.post("/crossword/generate", json={"theme": ""})
    assert res.status_code == 400
    assert "must include" in res.json()["detail"]


def test_get_solo_without_generation_returns_404(client):
    """Test that /solo returns 404 when no crossword exists."""
    # Clear any existing files first
    client.delete("/crossword/test/clear-all")
    
    res = client.get("/crossword/solo")
    assert res.status_code == 404
    assert "No solo crossword available" in res.json()["detail"]


def test_get_battle_without_generation_returns_404(client):
    """Test that /battle returns 404 when no crossword exists."""
    # Clear any existing files first
    client.delete("/crossword/test/clear-all")
    
    res = client.get("/crossword/battle")
    assert res.status_code == 404
    assert "No battle crossword available" in res.json()["detail"]


def test_test_clear_all_returns_success(client):
    """Test that /test/clear-all returns success response."""
    res = client.delete("/crossword/test/clear-all")
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert "deleted_files" in data