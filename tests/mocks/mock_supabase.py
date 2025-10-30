class MockResponse:
    def __init__(self, data):
        self.data = data


class MockTable:
    def __init__(self, name):
        self.name = name
        self.inserted = []
        self.filters = []

    def insert(self, data):
        self.inserted.append(data)
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        results = self.inserted
        for field, value in self.filters:
            results = [row for row in results if row.get(field) == value]
        self.filters = []
        return MockResponse(results)


class MockSupabase:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = MockTable(name)
        return self.tables[name]
