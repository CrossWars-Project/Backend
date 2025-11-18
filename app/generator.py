# backend/api.py
"""
Flask API endpoint that:
 - Accepts POST /api/generate with JSON { "theme": "ocean" }
 - Runs the OpenAI -> pycrossword pipeline (words -> clues -> crossword)
 - Writes a JSON file backend/latest_crossword.json with the full output
 - Returns the same JSON response to the caller
This file is additive — it does not change existing scripts.

Requires:
- flask
- Python 3.12+ (use .venv313)
- OPENAI package (pip install openai)
- pycrossword package (pip install pycrossword)
 -For setup and operation, read generator_README.md file.
 - ALWAYS USE INSIDE VENV313!!
"""

import os
import json
import re
from pathlib import Path
from typing import List
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

# ------------------ Put your OpenAI API key here ------------------
OPENAI_API_KEY = api_key
# ------------------------------------------------------------------

# OpenAI Responses client
from openai import OpenAI

# pycrossword documented imports
from pycrossword import generate_crossword
from pycrossword import OpenAIClient, ClueGenerator, ClueDifficulty


# CLI-style render function from pycrossword._utils (copied behavior)
def render_crossword(placed_words: list, dimensions: list):
    grid = [["-" for _ in range(dimensions[0])] for _ in range(dimensions[1])]
    for items in placed_words:
        if items[3]:
            for i in range(len(items[0])):
                grid[items[1]][items[2] + i] = items[0][i]
        else:
            for i in range(len(items[0])):
                grid[items[1] + i][items[2]] = items[0][i]
    return grid


# NEW: Pad grid to 5x5
def pad_grid_to_5x5(grid: list) -> list:
    """
    Pad a grid to be exactly 5x5 by adding rows/columns of dashes.
    """
    TARGET_SIZE = 5
    current_rows = len(grid)
    current_cols = len(grid[0]) if grid else 0

    # Pad columns (add dashes to the right of each row)
    if current_cols < TARGET_SIZE:
        for row in grid:
            row.extend(["-"] * (TARGET_SIZE - current_cols))

    # Pad rows (add new rows at the bottom)
    if current_rows < TARGET_SIZE:
        for _ in range(TARGET_SIZE - current_rows):
            grid.append(["-"] * TARGET_SIZE)

    return grid


# Convert list/tuple output into JSON-serializable structure if necessary
def _to_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_serializable(v) for v in list(obj)]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


# parse model text into list of words (robust)
def parse_words_from_model(text: str) -> List[str]:
    text = (text or "").strip()
    # try json
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(w).strip().upper() for w in parsed if isinstance(w, (str, int))]
    except Exception:
        pass
    # try extract json array inside text
    m = re.search(r"(\[.*\])", text, flags=re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list):
                return [
                    str(w).strip().upper() for w in parsed if isinstance(w, (str, int))
                ]
        except Exception:
            pass
    # fallback split
    tokens = re.split(r"[,\n\r;]+", text)
    words = []
    for t in tokens:
        t = re.sub(r"[^A-Za-z]", "", t).strip().upper()
        if 1 <= len(t) <= 5:
            words.append(t)
    return words


# Ask OpenAI Responses API for words given a theme
def ask_openai_for_words(
    theme: str, max_words: int = 16, max_output_tokens: int = 1000
) -> List[str]:
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-REPLACE"):
        raise RuntimeError(
            "OPENAI_API_KEY not set inside backend/api.py. Please edit file and add your key."
        )
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    client = OpenAI()

    # UPDATED PROMPT
    prompt = (
        f'Return a JSON array (e.g. ["ATOM","STAR","RAIN",...]) of up to {max_words} single-word terms '
        f'related to the theme "{theme}". '
        "IMPORTANT RULES:\n"
        "- ALL words must be EXACTLY 3 letters long (no 5-letter words)\n"
        "- Prefer words with common letters like A, E, I, O, R, S, T, N\n"
        "- Use simple, common words that are easy to crossword\n"
        "- Return ONLY the JSON array with no commentary or explanations"
    )

    resp = client.responses.create(
        model="gpt-5-2025-08-07",
        input=prompt,
        max_output_tokens=max_output_tokens,
        reasoning={"effort": "low"},
    )

    # get aggregated text
    output_text = getattr(resp, "output_text", None)
    if output_text is None:
        parts = []
        for item in getattr(resp, "output", []):
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
        output_text = "\n".join(parts)

    words = parse_words_from_model(output_text)

    # UPDATED: enforce 3-4 letters only (filter out 5-letter words)
    seen = set()
    filtered = []
    for w in words:
        w2 = w.strip().upper()
        if 3 <= len(w2) <= 4 and w2.isalpha() and w2 not in seen:
            filtered.append(w2)
            seen.add(w2)
    return filtered[:max_words]


# Generate clues using pycrossword's ClueGenerator (documented API)
def generate_clues(words: List[str]) -> dict:
    # using pycrossword's OpenAIClient and ClueGenerator
    ai_client = OpenAIClient(OPENAI_API_KEY)
    clue_generator = ClueGenerator(ai_client, difficulty=ClueDifficulty.MEDIUM)
    clues = clue_generator.create(words)
    # clue_generator.create returns a mapping word -> list of clue strings per docs
    return clues


# Build final JSON response, write to latest_crossword.json
def build_and_save(theme: str):
    # 1) get words
    words = ask_openai_for_words(theme, max_words=16, max_output_tokens=1500)
    if not words:
        raise RuntimeError("OpenAI did not return usable words. Try a different theme.")

    # 2) generate clues (if clue generation fails continue without clues but log)
    try:
        clues = generate_clues(words)
    except Exception as e:
        # If clues fail, set clues=None but continue to generate crossword (per your earlier desire)
        clues = None

    # 3) generate crossword (pycrossword documented usage)
    dimensions, placed_words = generate_crossword(words.copy(), x=5, y=5)

    # 4) render grid CLI-style
    grid = render_crossword(placed_words, dimensions)

    # NEW: Pad grid to ensure it's always 5x5
    grid = pad_grid_to_5x5(grid)
    dimensions = (5, 5)  # Update dimensions to reflect padded size

    # 5) organize clues by across/down
    if clues:
        across_clues = [
            clues[p[0]][0]
            for p in placed_words
            if p[3] and clues.get(p[0]) and clues[p[0]]
        ]
        down_clues = [
            clues[p[0]][0]
            for p in placed_words
            if not p[3] and clues.get(p[0]) and clues[p[0]]
        ]
    else:
        across_clues = []
        down_clues = []

    # 6) create JSON structure
    response_obj = {
        "theme": theme,
        "words_sent": words,
        "dimensions": {"cols": dimensions[0], "rows": dimensions[1]},
        "placed_words": [[p[0], p[1], p[2], bool(p[3])] for p in placed_words],
        "grid": grid,
        "clues": _to_json_serializable(clues) if clues else None,
        "clues_across": across_clues,
        "clues_down": down_clues,
    }

    # 7) write to file
    out_path = Path(__file__).parent / "latest_crossword.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(response_obj, f, indent=2)

    return response_obj


# Flask app
app = Flask(__name__)
CORS(app)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json(force=True, silent=True) or {}
    theme = (body.get("theme") or "").strip()
    if not theme:
        return make_response(
            jsonify({"error": 'theme required in JSON body {"theme":"..."}'}), 400
        )
    try:
        result = build_and_save(theme)
        return jsonify(result)
    except Exception as e:
        return make_response(
            jsonify({"error": "generation failed", "details": str(e)}), 500
        )


@app.route("/api/latest", methods=["GET"])
def api_latest():
    file_path = Path(__file__).parent / "latest_crossword.json"
    if not file_path.exists():
        return make_response(jsonify({"error": "no latest crossword file"}), 404)
    with open(file_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    # quick local run
    app.run(host="127.0.0.1", port=5000, debug=True)
