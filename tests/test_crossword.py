# tests/test_crossword.py
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import os


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def cleanup_test_files():
    """Clean up test crossword files after each test."""
    yield
    # Cleanup after test
    from app import generator
    app_dir = Path(generator.__file__).parent
    test_files = ["solo_play.json", "battle_play.json", "latest_crossword.json"]
    for filename in test_files:
        file_path = app_dir / filename
        if file_path.exists():
            os.remove(file_path)


def test_generate_daily_creates_both_crosswords(client, cleanup_test_files):
    """Test that /generate-daily creates both solo and battle crosswords."""
    res = client.post("/crossword/generate-daily")
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert "solo" in data["results"]
    assert "battle" in data["results"]
    assert data["results"]["solo"]["status"] == "generated"
    assert data["results"]["battle"]["status"] == "generated"


def test_get_solo_crossword_returns_data(client, cleanup_test_files):
    """Test that /solo returns crossword data after generation."""
    # Generate crosswords first
    client.post("/crossword/generate-daily")
    
    # Get solo crossword
    res = client.get("/crossword/solo")
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert "grid" in data["data"]
    assert "clues_across" in data["data"]
    assert "clues_down" in data["data"]
    assert data["data"]["dimensions"]["cols"] == 5
    assert data["data"]["dimensions"]["rows"] == 5


def test_get_battle_crossword_returns_data(client, cleanup_test_files):
    """Test that /battle returns crossword data after generation."""
    # Generate crosswords first
    client.post("/crossword/generate-daily")
    
    # Get battle crossword
    res = client.get("/crossword/battle")
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert "grid" in data["data"]
    assert data["data"]["dimensions"]["cols"] == 5
    assert data["data"]["dimensions"]["rows"] == 5


def test_get_solo_without_generation_returns_404(client, cleanup_test_files):
    """Test that /solo returns 404 when no crossword exists."""
    res = client.get("/crossword/solo")
    assert res.status_code == 404
    assert "No solo crossword available" in res.json()["detail"]


def test_test_generate_new_creates_solo_only(client, cleanup_test_files):
    """Test that /test/generate-new can create solo crossword only."""
    res = client.post("/crossword/test/generate-new", json={"mode": "solo"})
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert "solo" in data["results"]
    assert "battle" not in data["results"]


def test_test_clear_all_deletes_files(client, cleanup_test_files):
    """Test that /test/clear-all removes crossword files."""
    # Generate first
    client.post("/crossword/test/generate-new")
    
    # Clear all
    res = client.delete("/crossword/test/clear-all")
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert len(data["deleted_files"]) > 0


def test_generate_with_custom_theme(client, cleanup_test_files):
    """Test that /generate accepts custom theme."""
    res = client.post("/crossword/generate", json={"theme": "ocean"})
    assert res.status_code == 200
    
    data = res.json()
    assert data["success"] is True
    assert data["data"]["theme"] == "ocean"


