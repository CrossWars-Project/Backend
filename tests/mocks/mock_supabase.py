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
        from datetime import datetime, timedelta

        # Generate ID if missing (real Supabase does this)
        if "id" not in data:
            data["id"] = str(uuid.uuid4())

        # Add default timestamps for invites
        if self.name == "invites":
            if "created_at" not in data:
                data["created_at"] = datetime.now().isoformat()
            if "expires_at" not in data:
                data["expires_at"] = (datetime.now() + timedelta(hours=24)).isoformat()
            if "status" not in data:
                data["status"] = "ACTIVE"  # Changed from True to "ACTIVE"

        # Store it (instead of sending to DB)
        self.inserted.append(data.copy())  # .copy() to avoid reference issues

        return self

    def select(self, fields="*"):
        """
        Real Supabase: Specifies columns to return
        Mock: Just remember the fields, apply in execute()
        """
        self.select_fields = fields
        return self

    def update(self, data):
        """
        Real Supabase: Updates rows in the database
        Mock: Just remember the data, apply in execute()
        """
        self.update_data = data
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))  # Store as tuple with type
        return self

    def execute(self):
        """Execute the query and return results"""
        if self.update_data:
            # Handle UPDATE operation
            updated_rows = []
            for row in self.inserted:
                # Apply ALL filters - ALL must match for update
                matches = True
                for filter_type, field, value in self.filters:
                    if filter_type == "eq" and row.get(field) != value:
                        matches = False
                        break

                if matches:
                    # Update this row
                    row.update(self.update_data)
                    updated_rows.append(row.copy())  # Return copy of updated row

            # Clear filters and update data for next query
            self.filters = []
            self.update_data = None
            return MockResponse(updated_rows)

        else:
            # Handle SELECT operation
            results = self.inserted.copy()

            # Apply filters
            for filter_type, field, value in self.filters:
                if filter_type == "eq":
                    results = [row for row in results if row.get(field) == value]

            # Clear filters for next query
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
