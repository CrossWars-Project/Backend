import pytest
import os


@pytest.fixture(autouse=True)
def set_testing_env(monkeypatch):
    # Only set TESTING=1 when running pytest
    if os.getenv("PYTEST_CURRENT_TEST"):
        monkeypatch.setenv("TESTING", "1")
