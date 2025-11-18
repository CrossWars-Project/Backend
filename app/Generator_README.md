Generator Setup & Usage — generator.py

Crossword Generator — Setup & Usage

This document explains how to configure and run the crossword generator module (app/generator.py) that integrates OpenAI + pycrossword-generator and exposes endpoints via the existing FastAPI app through app/routes/crossword.py.

# Important: pycrossword-generator requires Python 3.12 or newer. Make sure you use a Python interpreter >= 3.12 for the environment where the generator runs.

1 — Prerequisites

Python >= 3.12 (3.13 is fine).

If your system default is older (e.g. 3.11), create a dedicated venv with a 3.12+ interpreter (instructions below).

Node/npm (only if you run a frontend locally; not required for the generator)

Access to an OpenAI API key -  key is locally stored in the 
generator.py file

2 — Recommended virtual environment (create & activate)
Windows (PowerShell) — using Python 3.13 if installed

# create a venv using Python launcher for 3.13 (or 3.12)

The Venv313 folder sholuld already be created, in that case simply activate it using .\.venv313\Scripts\Activate.ps1 command

If the venv313 file is not there, install it first:
py -3.13 -m venv .venv313

# activate venv in PowerShell
.\.venv313\Scripts\Activate.ps1

macOS / Linux
# if python3.12 is installed:
The Venv313 folder sholuld already be created, in that case simply activate it using .\.venv313\Scripts\Activate.ps1 command

If the venv313 file is not there, install it first:

python3.12 -m venv .venv312 or py -m venv .venv312
source .venv312/bin/activate


If you do not have Python 3.12/3.13 installed, install it (e.g. from python.org, pyenv, or system package manager) before creating the venv. (you can che check pythin version using python --version)

TIP: Even if you are using python > 3.12 STILL USE THE VENV313. This is because VSCode can glitch and will revert your python to 3.11. 

# So use the Venv313 in either case!

# Once you are venv313, run python --version. if You see version >=3.12, then you are good to go. If not contact Kiannskkandann@gmail.com

Once you are in venv313, run this script:

pip install --upgrade pip setuptools wheel
pip install -r generator-requirements.txt

Once the packages are installed, you can run start the backend:

python generator.py




3 — Output JSON format (what the frontend will receive)

Example structure returned by POST /crossword/generate and saved to latest_crossword.json:

{
  "theme": "OCEAN",
  "words_sent": ["WAVE","SHIP", ...],      // words requested from OpenAI (<=5 letters)
  "dimensions": { "cols": 5, "rows": 5 },
  "placed_words": [
    ["WAVE", 0, 0, true],                  // [word, row, col, horizontal?]
    ["SHIP", 2, 0, false]
  ],
  "grid": [
    ["W","A","V","E","-"],
    ["-","-","-","-","-"],
    ["S","-","-","-","-"],
    ["H","-","-","-","-"],
    ["I","-","-","-","-"]
  ],
  "clues": {
    "WAVE": ["A ridge of water moving across the sea."],
    "SHIP": ["A large vessel for maritime transport."]
  },
  "clues_across": ["A ridge of water moving across the sea."],
  "clues_down": ["A large vessel for maritime transport."]
}


Frontend can render grid (5×5) directly and display clues_across / clues_down arrays.

placed_words can be used to map highlighting and numbering.

4 — Troubleshooting & tips

pycrossword-generator install fails — check Python version. Ensure venv uses Python >= 3.12. Use py -3.13 -m venv .venv313 (Windows) or python3.12 -m venv .venv312 (Unix).

No OpenAI output / empty words — increase max_output_tokens in ask_openai_for_words() (default used in generator is 1500). Ensure OPENAI_API_KEY is correct and has quota.

Clues empty — ClueGenerator.create() sometimes returns empty lists; code extracts clues only when present. Check latest_crossword.json clues field to inspect raw clue mappings.

CORS errors (frontend) — ensure frontend origin is allowed in main.py CORSMiddleware. Add http://localhost:5173 or your dev URL.

Port conflicts — run uvicorn on a different port: uvicorn app.main:app --reload --port 8001.

