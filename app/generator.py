# backend/app/generator.py
"""
Crossword generator that:
 - Uses OpenAI API to generate themed words
 - Uses pycrossword to arrange words into a 5x5 grid
 - Generates clues for each word
 - Writes output to latest_crossword.json and Supabase Storage

Requires:
- Python 3.12+
- openai package (pip install openai)
- pycrossword package (pip install pycrossword)
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


# Pad grid to 5x5
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
        if 3 <= len(t) <= 5:
            words.append(t)
    return words


# Ask OpenAI Responses API for words given a theme
def ask_openai_for_words(
    theme: str, max_words: int = 30, max_output_tokens: int = 5000
) -> List[str]:
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-REPLACE"):
        raise RuntimeError(
            "OPENAI_API_KEY not set inside backend/api.py. Please edit file and add your key."
        )
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    client = OpenAI()

    # UPDATED PROMPT: Request 25+ words with variety in length
    prompt = (
        f'Return a JSON array of at least 30 single-word terms related to the theme "{theme}". '
        "IMPORTANT RULES:\n"
        "- Words must be 3, 4, or 5 letters long\n"
        "- Prioritize mostly 3-letter words (about 60%)\n"
        "- Include some 4-letter words (about 30%)\n"
        "- Include a few 5-letter words (about 10%)\n"
        "- Prefer words with common letters like A, E, I, O, R, S, T, N\n"
        "- Use simple, common words that work well in crosswords\n"
        '- Return ONLY the JSON array (e.g. ["DOG","TREE","OCEAN",...]) with no commentary or explanations'
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

    # UPDATED: enforce 3-5 letters and uniqueness
    seen = set()
    filtered = []
    for w in words:
        w2 = w.strip().upper()
        if 3 <= len(w2) <= 5 and w2.isalpha() and w2 not in seen:
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


def save_to_supabase_storage(data: dict, filename: str):
    """Save crossword data to Supabase Storage bucket"""
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print(
            "Warning: Supabase credentials missing, falling back to local storage only"
        )
        return False

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Convert data to JSON string
        json_data = json.dumps(data, indent=2)

        # Upload to Supabase Storage (create 'crosswords' bucket in Supabase dashboard first)
        supabase.storage.from_("crosswords").upload(
            filename,
            json_data.encode("utf-8"),
            file_options={"content-type": "application/json", "upsert": "true"},
        )

        print(f"✅ Successfully saved {filename} to Supabase Storage")
        return True
    except Exception as e:
        print(f"❌ Error saving to Supabase Storage: {e}")
        return False


def detect_overlapping_substrings(placed_words: list) -> tuple:
    """
    Detect if any word is a substring of another word at the same position with same orientation.
    Returns (has_overlap, word_to_remove) where word_to_remove is the shorter word.
    """
    position_map = {}  # Map (row, col, is_across) -> word

    for word_data in placed_words:
        word, row, col, is_across = word_data
        key = (row, col, is_across)

        if key in position_map:
            existing_word = position_map[key]
            # Check if one is a substring of the other
            if word in existing_word or existing_word in word:
                # Return the shorter word to remove
                shorter = word if len(word) < len(existing_word) else existing_word
                print(
                    f"⚠️  Detected overlap: '{word}' and '{existing_word}' at same position"
                )
                print(f"   Will retry without '{shorter}'")
                return (True, shorter)
        else:
            position_map[key] = word

    return (False, None)


# Build final JSON response, write to latest_crossword.json
def build_and_save(theme: str):
    # 1) get words - request 30 words for more variety
    words = ask_openai_for_words(theme, max_words=30, max_output_tokens=5000)
    if not words:
        raise RuntimeError("OpenAI did not return usable words. Try a different theme.")

    print(f"Generated {len(words)} words: {words}")

    # 2) generate clues (if clue generation fails continue without clues but log)
    try:
        clues = generate_clues(words)
    except Exception as e:
        print(f"Clue generation failed: {e}")
        clues = None

    # 3) generate crossword with retry logic for overlapping substrings
    max_retries = 5
    words_to_use = words.copy()

    for attempt in range(max_retries):
        print(
            f"\nAttempt {attempt + 1}: Generating crossword with {len(words_to_use)} words..."
        )
        dimensions, placed_words = generate_crossword(words_to_use.copy(), x=5, y=5)

        # Check for overlapping substrings at same position
        has_overlap, word_to_remove = detect_overlapping_substrings(placed_words)

        if not has_overlap:
            print(f"✅ Success! Placed {len(placed_words)} words with no overlaps")
            break
        else:
            # Remove the problematic word and retry
            words_to_use = [w for w in words_to_use if w != word_to_remove]
            if attempt == max_retries - 1:
                print(f"⚠️  Max retries reached. Using current placement.")
                # Remove the duplicate from placed_words
                position_map = {}
                cleaned_placed_words = []
                for word_data in placed_words:
                    word, row, col, is_across = word_data
                    key = (row, col, is_across)
                    if key in position_map:
                        existing = position_map[key]
                        # Keep longer word
                        if len(word) > len(existing):
                            cleaned_placed_words = [
                                w for w in cleaned_placed_words if w[0] != existing
                            ]
                            cleaned_placed_words.append(word_data)
                            position_map[key] = word
                    else:
                        cleaned_placed_words.append(word_data)
                        position_map[key] = word
                placed_words = cleaned_placed_words

    # 4) render grid CLI-style
    grid = render_crossword(placed_words, dimensions)

    # Pad grid to ensure it's always 5x5
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

    # 7) write to local file (for local development)
    out_path = Path(__file__).parent / "latest_crossword.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(response_obj, f, indent=2)

    # 8) ALSO save to Supabase Storage (for production persistence)
    save_to_supabase_storage(response_obj, "latest_crossword.json")

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
