# tests/test_generator.py
"""
Tests for the crossword generator FastAPI routes.
"""

import json
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app  # FastAPI app from the bigger project

client = TestClient(app)


def test_generate_endpoint_success_returns_generated_json():
    """
    ARRANGE:
    - Provide a fake build_and_save that returns a known sample.
    - This verifies that the generate endpoint forwards the generator result correctly.
    """
    sample = {
        "theme": "TEST",
        "words_sent": ["A", "B"],
        "dimensions": {"cols": 5, "rows": 5},
        "placed_words": [["A", 0, 0, True]],
        "grid": [["A", "-", "-", "-", "-"], ["-", "-", "-", "-", "-"], ["-", "-", "-", "-", "-"], ["-", "-", "-", "-", "-"], ["-", "-", "-", "-", "-"]],
        "clues": {"A": ["Clue A"]},
        "clues_across": ["Clue A"],
        "clues_down": []
    }

    # ARRANGE: monkeypatch the generator to return the sample result
    import app.generator as gen_mod
    original = getattr(gen_mod, "build_and_save", None)
    try:
        gen_mod.build_and_save = lambda theme: sample

        # ACT: call the endpoint
        resp = client.post("/crossword/generate", json={"theme": "test-theme"})

        # ASSERT: endpoint returns success wrapper and the exact data
        assert resp.status_code == 200
        body = resp.json()
        assert "success" in body and body["success"] is True
        assert "data" in body and body["data"] == sample
    finally:
        # restore original if present
        if original is not None:
            gen_mod.build_and_save = original


def test_generate_endpoint_missing_theme_returns_400_bad_request():
    """
    ARRANGE:
    - No theme provided in the request body.
    - This ensures the endpoint validates input and returns an appropriate HTTP 400.
    """

    # ACT: call generate without theme
    resp = client.post("/crossword/generate", json={})

    # ASSERT: should be 400 with helpful detail
    assert resp.status_code == 400
    body = resp.json()
    # detail should explain missing theme requirement
    assert "detail" in body
    assert "must include" in body["detail"] or "theme" in body["detail"].lower()


def test_generate_endpoint_generator_failure_returns_500():
    """
    ARRANGE:
    - Monkeypatch build_and_save to raise an exception.
    - This verifies that the endpoint maps internal failures to HTTP 500 with a clear message.
    """
    import app.generator as gen_mod
    original = getattr(gen_mod, "build_and_save", None)

    def _raise(theme):
        raise Exception("simulated generator failure")

    try:
        gen_mod.build_and_save = _raise

        # ACT: call endpoint which will invoke the failing build_and_save
        resp = client.post("/crossword/generate", json={"theme": "anything"})

        # ASSERT: 500 and contains the original error message
        assert resp.status_code == 500
        body = resp.json()
        assert "detail" in body
        assert "simulated generator failure" in body["detail"]
    finally:
        # restore original
        if original is not None:
            gen_mod.build_and_save = original


def test_latest_endpoint_reads_latest_crossword_file_success(tmp_path):
    """
    ARRANGE:
    - Create a latest_crossword.json next to the app.generator module so the endpoint can read it.
    - This verifies the /crossword/latest endpoint returns the saved JSON correctly.
    """
    # ensure generator module is importable and determine where it writes latest_crossword.json
    gen_mod = importlib.import_module("app.generator")
    file_path = Path(gen_mod.__file__).parent / "latest_crossword.json"

    sample = {"hello": "world"}
    try:
        # ARRANGE: write a sample file
        file_path.write_text(json.dumps(sample), encoding="utf-8")

        # ACT: call the endpoint
        resp = client.get("/crossword/latest")

        # ASSERT: should return 200 and the same data
        assert resp.status_code == 200
        body = resp.json()
        assert "success" in body and body["success"] is True
        assert "data" in body and body["data"] == sample
    finally:
        # cleanup the sample file
        if file_path.exists():
            file_path.unlink()
