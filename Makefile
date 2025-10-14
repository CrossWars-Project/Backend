.PHONY: format check-format typecheck

# Reformat all Python files with Black
format:
	black .

# Check that code is properly formatted (fails if not)
check-format:
	black --check .

# Run mypy for type checking
typecheck:
	mypy .
