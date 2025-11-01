class MockUser:
    """Mock Supabase User"""

    def __init__(self, user_id, email, username=None):
        self.id = user_id
        self.email = email
        self.user_metadata = {"username": username} if username else {}


class MockResponse:
    def __init__(self, data):
        self.data = data


class MockAuth:
    """Mock Supabase Auth Client"""

    def __init__(self):
        self.valid_tokens = {}

    def add_user(self, token, user_id, email, username=None):
        """help add a valid user token for testing"""
        self.valid_tokens[token] = MockUser(user_id, email, username)

    def get_user(self, token):
        """Mock get user by token"""
        if token in self.valid_tokens:
            return MockUserResponse(self.valid_tokens[token])

        raise Exception("Invalid token")


class MockUserResponse:
    def __init__(self, user):
        self.user = user


class MockTable:
    def __init__(self, name):
        self.name = name  # Table name
        self.inserted = []  # List to store inserted rows
        self.filters = []  # List of filters applied
        self.update_data = None  # Data for update operations
        self.select_fields = "*"  # Fields to select

    def insert(self, data):
        """
        Real Supabase: Sends data to database
        Mock: Just append to a list
        """
        import uuid

        # Generate ID if missing (real Supabase does this)
        if "id" not in data:
            data["id"] = str(uuid.uuid4())

        # Store it (instead of sending to DB)
        self.inserted.append(data.copy())  # .copy() to avoid reference issues

        return self

    # def select(self, *args, **kwargs):

    #   return self
    def select(self, fields="*"):
        """
        Real Supabase: Specifies columns to return
        Mock: Just remember the fields, apply in execute()
        """
        self.select_fields = fields
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
        self.auth = MockAuth()

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = MockTable(name)
        return self.tables[name]

    def reset(self):
        """Reset all tables (for test isolation)"""
        self.tables = {}
        self.auth = MockAuth()
