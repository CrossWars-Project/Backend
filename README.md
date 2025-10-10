# Backend
Python scripts and crossword generation

# TODOs:
    - linter
    - continious intergation setup (aka update testing setup)

# Backend — CrossWars Project

This repository contains the **backend API** for the CrossWars project.  
It uses **FastAPI** as the web framework, **Supabase** as the database and authentication layer, and is designed to connect with the **React.js frontend** (stored in a separate repo).

---

## 🚀 Tech Stack

| Component | Technology |
|------------|-------------|
| Language | Python 3.10+ |
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | [Supabase (PostgreSQL)](https://supabase.com) |
| ORM / Client | [supabase-py](https://github.com/supabase-community/supabase-py) |
| Server | [Uvicorn](https://www.uvicorn.org/) |
| Environment | Virtualenv (`venv`) |
| Editor | [VS Code](https://code.visualstudio.com/) |


--- 
## Setup
### Prerequisites

Make sure you have the following installed or access to **before starting**:

- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- [VS Code](https://code.visualstudio.com/)
- A [Supabase](https://supabase.com) project (ask the team for the credentials)

---

### 1. Clone the Repository

### 2. Create and Activate a Virtual Environment
- In you VS terminal run
    >> python -m venv venv
    >> venv\Scripts\activate
### 3. Install Dependencies
- In your VS terminal run
    >> pip install -r requirements.txt
- If you add new packages later update requirements.txt with
    >> pip freeze > requirements
### 4. Create a .env File
- The project ID and key can be found in the supabase project settings under API Keys

    SUPABASE_URL="https://yourprojectid.supabase.co"
    SUPABASE_KEY="your-anon-or-service-role-key"
    
### 5. Run the Development Server and Check
- in terminal run 
   >> uvicorn app.main:app --reload
 - visit http://127.0.0.1:8000 to check if its working, should see { "message": "Hello from FastAPI backend!" }
 
### Testing

Run the test suite from the project root. If your virtual environment is active, either run `pytest` or run it via Python to ensure the correct interpreter is used:

PowerShell (recommended when venv is active):
```powershell
python -m pytest -q
```

If pytest can't find the `app` package during collection you have a few simple options:

- Keep `pytest.ini` in the project root (used in this repo). It sets the test `pythonpath = .` so `from app...` resolves during test collection.
- Install the package in editable mode (recommended for development):
```powershell
python -m pip install -e .
```
This requires a minimal packaging file such as `pyproject.toml` or `setup.cfg` in the repo root.
- Or set PYTHONPATH for the test run (temporary):
```powershell
$env:PYTHONPATH = (Get-Location).Path; python -m pytest -q
```

Notes on choices:
- `pytest.ini` is the quickest, least-invasive fix for classroom or small repos. It's what this repository currently uses.
- Editable install (`pip install -e .`) is cleaner for active development or CI because it makes the package importable for all Python runs, not just pytest.

### Additional setup notes
- I had issues with the supabase import on db.py.
- If vev prompts: use venv interpreter .venv/Scripts/python.exe
- If no prompt but having issue:
    1. Ctrl + Shift + P
    2. Type Python:Select Interpreter
    3. choose the one that says venv and includes python.exe
 --

## Typical Workflow
 - 1. Start from latest main branch
    >> git checkout main
    >> git pull origin main
 - 2. checkout a branch using checkout or switch
    >> git checkout -b <feature-or-fix>/<description>
    >> git switch -c <feature-or-fix>/<description>
 - 2. Activate venv
    >> venv/Scripts/activate
 - 3. Make code changes
    -> keep commits small and descriptive
    -> commit for feature change
    -> commit for new tests you need to write
    -> commit for documentation
 - 4. Run test
    >> uvicorn app.main:app --reload
    >> python -m pytest
 - 5. Push branch to origin
    >> git push origin <branch-name>
 - 6. End dev session aka leave venv
    >> deactivate
 - 7. Open Pull Request 
 - 8. Automated testing/ code review
 - 9. Merge to main
