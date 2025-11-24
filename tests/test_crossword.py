import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from fastapi.testclient import TestClient

# Mock crossword data that matches generator.py output structure
MOCK_CROSSWORD_DATA = {
    "theme": "technology",
    "words_sent": ["CODE", "DATA", "TECH", "BYTE", "CPU"],
    "dimensions": {"cols": 5, "rows": 5},
    "placed_words": [
        ["CODE", 0, 0, True],
        ["DATA", 1, 0, False],
        ["TECH", 2, 1, True],
    ],
    "grid": [
        ["C", "O", "D", "E", "-"],
        ["D", "-", "-", "-", "-"],
        ["A", "T", "E", "C", "H"],
        ["T", "-", "-", "-", "-"],
        ["A", "-", "-", "-", "-"],
    ],
    "clues": {
        "CODE": ["Instructions for computers"],
        "DATA": ["Information processed by computers"],
        "TECH": ["Short for technology"],
    },
    "clues_across": ["Instructions for computers", "Short for technology"],
    "clues_down": ["Information processed by computers"],
}


@pytest.fixture
def mock_generator_module():
    """
    Mock the entire generator module to avoid real OpenAI API calls
    and file I/O operations
    """
    with patch("app.routes.crossword.generator") as mock_gen:
        # Mock build_and_save to return our mock data without actually calling OpenAI
        mock_gen.build_and_save = MagicMock(return_value=MOCK_CROSSWORD_DATA)
        yield mock_gen


@pytest.fixture
def mock_file_operations():
    """Mock file operations to avoid actual file I/O during tests"""
    app_dir = Path(__file__).parent.parent / "app"

    def mock_exists(self):
        # Control which files "exist" for testing
        filename = self.name
        if filename in ["solo_play.json", "battle_play.json", "latest_crossword.json"]:
            return False  # Default to not existing
        return True

    with patch.object(Path, "exists", mock_exists):
        yield


@pytest.fixture
def create_test_file():
    """Helper to create actual test files that get cleaned up"""
    created_files = []

    def _create(filename, data):
        app_dir = Path(__file__).parent.parent / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        file_path = app_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        created_files.append(file_path)
        return file_path

    yield _create

    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()


def test_generate_crossword_success(mock_generator_module):
    """Test successful crossword generation with a theme"""
    from app.main import app

    client = TestClient(app)

    payload = {"theme": "technology"}
    res = client.post("/crossword/generate", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["theme"] == "technology"
    assert "grid" in data["data"]
    assert "clues" in data["data"]
    mock_generator_module.build_and_save.assert_called_once_with("technology")


def test_generate_crossword_missing_theme():
    """Test that missing theme returns 400 error"""
    from app.main import app

    client = TestClient(app)

    # Empty payload
    res = client.post("/crossword/generate", json={})
    assert res.status_code == 400
    assert "theme" in res.json()["detail"].lower()

    # Missing theme key
    res2 = client.post("/crossword/generate", json={"other": "value"})
    assert res2.status_code == 400


def test_generate_crossword_whitespace_theme():
    """Test that whitespace-only theme returns 400 error"""
    from app.main import app

    client = TestClient(app)

    res = client.post("/crossword/generate", json={"theme": "   "})
    assert res.status_code == 400


def test_generate_crossword_strips_whitespace(mock_generator_module):
    """Test that theme whitespace is properly stripped"""
    from app.main import app

    client = TestClient(app)

    res = client.post("/crossword/generate", json={"theme": "  technology  "})
    assert res.status_code == 200
    mock_generator_module.build_and_save.assert_called_once_with("technology")


def test_get_solo_crossword_not_found():
    """Test that GET /crossword/solo returns 404 when file doesn't exist"""
    from app.main import app

    client = TestClient(app)

    # Ensure file doesn't exist
    app_dir = Path(__file__).parent.parent / "app"
    solo_path = app_dir / "solo_play.json"
    if solo_path.exists():
        solo_path.unlink()

    res = client.get("/crossword/solo")
    assert res.status_code == 404
    assert "solo crossword" in res.json()["detail"].lower()


def test_get_battle_crossword_not_found():
    """Test that GET /crossword/battle returns 404 when file doesn't exist"""
    from app.main import app

    client = TestClient(app)

    # Ensure file doesn't exist
    app_dir = Path(__file__).parent.parent / "app"
    battle_path = app_dir / "battle_play.json"
    if battle_path.exists():
        battle_path.unlink()

    res = client.get("/crossword/battle")
    assert res.status_code == 404
    assert "battle crossword" in res.json()["detail"].lower()


def test_get_latest_crossword_not_found():
    """Test that GET /crossword/latest returns 404 when file doesn't exist"""
    from app.main import app

    client = TestClient(app)

    # Ensure file doesn't exist
    app_dir = Path(__file__).parent.parent / "app"
    latest_path = app_dir / "latest_crossword.json"
    if latest_path.exists():
        latest_path.unlink()

    res = client.get("/crossword/latest")
    assert res.status_code == 404


def test_get_solo_crossword_success(create_test_file):
    """Test successful retrieval of solo crossword"""
    from app.main import app

    client = TestClient(app)

    # Create a mock solo_play.json file
    create_test_file("solo_play.json", MOCK_CROSSWORD_DATA)

    res = client.get("/crossword/solo")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["theme"] == "technology"
    assert "grid" in data["data"]


def test_get_battle_crossword_success(create_test_file):
    """Test successful retrieval of battle crossword"""
    from app.main import app

    client = TestClient(app)

    # Create a mock battle_play.json file
    create_test_file("battle_play.json", MOCK_CROSSWORD_DATA)

    res = client.get("/crossword/battle")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["theme"] == "technology"


def test_get_latest_crossword_success(create_test_file):
    """Test successful retrieval of latest crossword"""
    from app.main import app

    client = TestClient(app)

    # Create a mock latest_crossword.json file
    create_test_file("latest_crossword.json", MOCK_CROSSWORD_DATA)

    res = client.get("/crossword/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["theme"] == "technology"


def test_test_generate_new_both_modes(mock_generator_module):
    """Test generating both solo and battle crosswords"""
    from app.main import app

    client = TestClient(app)

    # Mock shutil.copy2 to avoid actual file operations
    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post("/crossword/test/generate-new", json={"mode": "both"})

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "solo" in data["results"]
    assert "battle" in data["results"]
    assert data["results"]["solo"]["status"] == "generated"
    assert data["results"]["battle"]["status"] == "generated"
    # Should be called twice (once for solo, once for battle)
    assert mock_generator_module.build_and_save.call_count == 2


def test_test_generate_new_solo_only(mock_generator_module):
    """Test generating only solo crossword"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post("/crossword/test/generate-new", json={"mode": "solo"})

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "solo" in data["results"]
    assert "battle" not in data["results"]
    mock_generator_module.build_and_save.assert_called_once()


def test_test_generate_new_battle_only(mock_generator_module):
    """Test generating only battle crossword"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post("/crossword/test/generate-new", json={"mode": "battle"})

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "battle" in data["results"]
    assert "solo" not in data["results"]
    mock_generator_module.build_and_save.assert_called_once()


def test_test_generate_new_custom_theme(mock_generator_module):
    """Test generating crossword with custom theme"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post(
            "/crossword/test/generate-new", json={"mode": "solo", "theme": "ocean"}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["results"]["solo"]["theme"] == "ocean"
    mock_generator_module.build_and_save.assert_called_with("ocean")


def test_test_generate_new_default_mode(mock_generator_module):
    """Test that default mode generates both solo and battle"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post("/crossword/test/generate-new")

    assert res.status_code == 200
    data = res.json()
    assert "solo" in data["results"]
    assert "battle" in data["results"]


def test_test_clear_all_crosswords(create_test_file):
    """Test clearing all crossword files"""
    from app.main import app

    client = TestClient(app)

    # Create some test files
    create_test_file("latest_crossword.json", MOCK_CROSSWORD_DATA)
    create_test_file("solo_play.json", MOCK_CROSSWORD_DATA)
    create_test_file("battle_play.json", MOCK_CROSSWORD_DATA)

    # Clear all files
    res = client.delete("/crossword/test/clear-all")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["deleted_files"]) == 3

    # Verify files are deleted
    app_dir = Path(__file__).parent.parent / "app"
    assert not (app_dir / "latest_crossword.json").exists()
    assert not (app_dir / "solo_play.json").exists()
    assert not (app_dir / "battle_play.json").exists()


def test_test_clear_all_when_no_files_exist():
    """Test clearing when no files exist"""
    from app.main import app

    client = TestClient(app)

    # Ensure no files exist
    app_dir = Path(__file__).parent.parent / "app"
    test_files = ["latest_crossword.json", "solo_play.json", "battle_play.json"]
    for filename in test_files:
        file_path = app_dir / filename
        if file_path.exists():
            file_path.unlink()

    res = client.delete("/crossword/test/clear-all")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["deleted_files"]) == 0


def test_generate_daily_crosswords(mock_generator_module):
    """Test daily crossword generation"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post("/crossword/generate-daily")

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "solo" in data["results"]
    assert "battle" in data["results"]
    assert data["results"]["solo"]["status"] == "generated"
    assert data["results"]["battle"]["status"] == "generated"
    assert "timestamp" in data
    # Should be called twice (once for solo, once for battle)
    assert mock_generator_module.build_and_save.call_count == 2


def test_generate_daily_uses_different_themes(mock_generator_module):
    """Test that daily generation uses different themes for solo and battle"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.shutil.copy2"):
        res = client.post("/crossword/generate-daily")

    assert res.status_code == 200
    data = res.json()

    # Verify different themes were used
    solo_theme = data["results"]["solo"]["theme"]
    battle_theme = data["results"]["battle"]["theme"]
    assert solo_theme != battle_theme


def test_generate_crossword_handles_generator_error():
    """Test that generation errors are properly handled"""
    from app.main import app

    client = TestClient(app)

    with patch("app.routes.crossword.generator") as mock_gen:
        mock_gen.build_and_save = MagicMock(side_effect=Exception("OpenAI API error"))

        res = client.post("/crossword/generate", json={"theme": "technology"})

        assert res.status_code == 500
        assert "error" in res.json()["detail"].lower() or "OpenAI" in str(
            res.json()["detail"]
        )


def test_get_crossword_handles_corrupted_json(create_test_file):
    """Test handling of corrupted JSON files"""
    from app.main import app

    client = TestClient(app)

    # Create a file with invalid JSON
    app_dir = Path(__file__).parent.parent / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    solo_path = app_dir / "solo_play.json"

    with open(solo_path, "w") as f:
        f.write("{ invalid json }")

    try:
        res = client.get("/crossword/solo")
        assert res.status_code == 500
    finally:
        if solo_path.exists():
            solo_path.unlink()
