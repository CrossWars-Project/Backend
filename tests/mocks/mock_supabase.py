import pytest


@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    """
    Mock Supabase client to prevent real database calls.
    Applied automatically to all tests in this file.
    """
    tables = {}

    class MockResponse:
        def __init__(self, data):
            self.data = data

    class MockTable:
        def __init__(self, name):
            self.name = name
            self.inserted = []
            self.filters = []  # store filters for chained queries

        def insert(self, data):
            self.inserted.append(data)
            return self  # allow chaining

        def select(self, *args, **kwargs):
            return self  # allow chaining

        def eq(self, field, value):
            # store filter instead of returning response immediately
            self.filters.append((field, value))
            return self  # allow chaining

        def execute(self):
            # Apply stored filters
            results = self.inserted
            for field, value in self.filters:
                results = [row for row in results if row.get(field) == value]
            self.filters = []  # reset filters after execution
            return MockResponse(results)

    class MockSupabase:
        def table(self, name):
            if name not in tables:
                tables[name] = MockTable(name)
            return tables[name]

    # Patch supabase in the app.db module
    monkeypatch.setattr("app.db.supabase", MockSupabase())
