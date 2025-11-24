# Generator Setup & Usage — generator.py

## Crossword Generator — Setup & Usage

This document explains how to configure and run the **daily crossword generator system** that integrates OpenAI + pycrossword-generator. The system automatically generates two different crosswords (Solo Play and Battle Play) daily at midnight via GitHub Actions.

**Important:** pycrossword-generator requires **Python 3.12 or newer** (Python 3.13 recommended).

---

## 1 — Prerequisites

- **Python >= 3.12** (3.13 recommended)
- **OpenAI API key** (stored in `.env` file)
- **Node/npm** (for frontend development)
- **GitHub repository** (for scheduled daily generation)

---

## 2 — Setup Virtual Environment

### macOS
```bash
# Navigate to backend
cd backend

# Check if .venv313 exists
ls -la | grep venv313

# If it exists, activate it:
source .venv313/bin/activate

# If it doesn't exist, create it:
python3.13 -m venv .venv313
source .venv313/bin/activate

# Verify Python version (should be >= 3.12)
python --version
```

### Windows (PowerShell)
```powershell
# Navigate to backend
cd backend

# If .venv313 exists, activate it:
.\.venv313\Scripts\Activate.ps1

# If it doesn't exist, create it:
py -3.13 -m venv .venv313
.\.venv313\Scripts\Activate.ps1

# Verify Python version (should be >= 3.12)
python --version
```

**Note:** Even if your system Python is >= 3.12, **still use .venv313** to avoid VS Code reverting to Python 3.11.

---

## 3 — Install Dependencies

### Backend Dependencies

Once activated in `.venv313`:
```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

### Frontend Dependencies
```bash
# Navigate to frontend
cd frontend

# Install all packages
npm install

# Install react-icons (required for UI icons)
npm install react-icons
```

**Important:** You must run `npm install react-icons` after `npm install` to ensure all icon dependencies are properly installed.

---

## 4 — Configure OpenAI API Key

Create or edit `backend/.env` file:
```env
OPENAI_API_KEY=sk-proj-your-actual-key-here
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-key-here
```

**Important:** 
- Do NOT use quotes around the API key!
- The `.env` file should be in the `backend/` directory (not `backend/app/`)

---

## 5 — How the System Works

### Production (Automatic Daily Generation)

1. **GitHub Actions** runs at **midnight UTC** (8 AM UTC = midnight PST)
2. Calls `POST /crossword/generate-daily` on your deployed backend
3. Generates **two crosswords**:
   - `solo_play.json` (for Solo Play mode)
   - `battle_play.json` (for Battle Play mode)
4. Files are saved to backend and overwrite previous day's crosswords
5. Frontend fetches crosswords via:
   - `GET /crossword/solo` (returns `solo_play.json`)
   - `GET /crossword/battle` (returns `battle_play.json`)

### Development (Manual Testing)

For local testing, you can manually trigger generation.

---

## 6 — Running Locally

### Start Backend Server
```bash
# Make sure you're in backend directory with venv activated
cd backend
source .venv313/bin/activate  # macOS
# OR
.\.venv313\Scripts\Activate.ps1  # Windows

# Start FastAPI server
uvicorn app.main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Start Frontend Server

In a **separate terminal**:
```bash
# Navigate to frontend
cd frontend

# Start development server
npm run dev
```

Frontend runs at: `http://localhost:5173`

You should see:
```
VITE v7.x.x  ready in XXX ms
➜  Local:   http://localhost:5173/
```

### Test Endpoints

Open a **third terminal** for testing:

**Generate fresh daily crosswords:**
```bash
curl -X POST http://127.0.0.1:8000/crossword/generate-daily
```

This takes 30-60 seconds. Expected response:
```json
{
  "success": true,
  "message": "Daily crosswords generated successfully",
  "results": {
    "solo": {"theme": "technology", "status": "generated"},
    "battle": {"theme": "nature", "status": "generated"}
  }
}
```

**Get solo crossword:**
```bash
curl http://127.0.0.1:8000/crossword/solo
```

**Get battle crossword:**
```bash
curl http://127.0.0.1:8000/crossword/battle
```

---

## 7 — Testing During Development

Since crosswords are generated once daily in production, we provide testing endpoints for development:

### Generate New Crossword for Testing
```bash
# Generate both solo and battle with random themes
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new

# Generate only solo
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new \
  -H "Content-Type: application/json" \
  -d '{"mode": "solo"}'

# Generate only battle
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new \
  -H "Content-Type: application/json" \
  -d '{"mode": "battle"}'

# Generate with custom theme
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new \
  -H "Content-Type: application/json" \
  -d '{"mode": "solo", "theme": "ocean"}'
```

### Clear All Crosswords (Test Error States)
```bash
curl -X DELETE http://127.0.0.1:8000/crossword/test/clear-all
```

This deletes all crossword files, useful for testing the "no crossword available" error state.

**See `TESTING_CROSSWORDS.md` for full testing documentation.**

---

## 8 — Testing the Full Flow

### Complete Test Workflow:

1. **Terminal 1 - Backend:**
```bash
   cd backend
   source .venv313/bin/activate
   uvicorn app.main:app --reload
```

2. **Terminal 2 - Frontend:**
```bash
   cd frontend
   npm run dev
```

3. **Terminal 3 - Generate Crossword:**
```bash
   curl -X POST http://127.0.0.1:8000/crossword/test/generate-new \
     -H "Content-Type: application/json" \
     -d '{"mode": "solo"}'
```
   Wait 30-60 seconds for completion.

4. **Test in Browser:**
   - Visit `http://localhost:5173`
   - Click "Solo Play"
   - Crossword should load instantly!

5. **Want a new crossword?** Repeat step 3.

---

## 9 — Output JSON Format

Crosswords are saved as JSON with this structure:
```json
{
  "theme": "technology",
  "words_sent": ["APP", "NET", "CODE", "DATA", "BOT", ...],
  "dimensions": { "cols": 5, "rows": 5 },
  "placed_words": [
    ["APP", 0, 0, true],    // [word, row, col, isAcross]
    ["NET", 1, 2, false],
    ["CODE", 2, 0, true]
  ],
  "grid": [
    ["A","P","P","-","-"],
    ["-","-","N","-","-"],
    ["C","O","D","E","-"],
    ["-","-","T","-","-"],
    ["-","-","-","-","-"]
  ],
  "clues": {
    "APP": ["Mobile application software."],
    "NET": ["Internet or mesh structure."],
    "CODE": ["Programming instructions."]
  },
  "clues_across": [
    "Mobile application software.",
    "Programming instructions."
  ],
  "clues_down": [
    "Internet or mesh structure."
  ]
}
```

### Field Descriptions:

- **theme**: The theme used for word generation
- **words_sent**: All words requested from OpenAI (25 words)
- **dimensions**: Grid size (always 5x5)
- **placed_words**: Words successfully placed in grid
- **grid**: 5x5 character array (letters and "-" for black squares)
- **clues**: Map of word → clue text
- **clues_across**: Clues for horizontal words (in order)
- **clues_down**: Clues for vertical words (in order)

---

## 10 — Key Features

- ✅ **Automatic daily generation** via GitHub Actions at midnight UTC
- ✅ **Two separate crosswords** (Solo & Battle modes)
- ✅ **Always 5x5 grid** (automatically padded if needed)
- ✅ **3-5 letter words** (mostly 3-letter for better placement)
- ✅ **25 words requested** from OpenAI (more options for pycrossword)
- ✅ **Theme rotation** (15 themes cycle based on day of year)
- ✅ **Testing endpoints** for development
- ✅ **Instant loading** for users (pre-generated)

---

## 11 — File Locations

### Backend Files:
- **Generator Logic:** `backend/app/generator.py`
- **API Routes:** `backend/app/routes/crossword.py`
- **Main App:** `backend/app/main.py`
- **Environment:** `backend/.env`
- **Requirements:** `backend/requirements.txt`

### Frontend Files:
- **Solo Play Component:** `frontend/src/components/SoloPlay/SoloPlay.jsx`
- **Battle Play Component:** `frontend/src/components/BattleScreen/` (future)

### Generated Files (gitignored):
- `backend/app/solo_play.json`
- `backend/app/battle_play.json`
- `backend/app/latest_crossword.json` (temp file)

### CI/CD:
- **GitHub Actions Workflow:** `.github/workflows/daily-crossword.yml`

---

## 12 — Troubleshooting

### "Command not found: uvicorn"
**Solution:** Activate virtual environment
```bash
source .venv313/bin/activate  # macOS
.\.venv313\Scripts\Activate.ps1  # Windows
```

### "Command not found: npm"
**Solution:** Install Node.js
```bash
# macOS
brew install node

# Windows
# Download from https://nodejs.org/
```

### "OpenAI did not return usable words"
**Causes & Solutions:**
- **API Key Issue:** Check `.env` file has correct key (no quotes!)
- **No Credits:** Check OpenAI account has available credits
- **Token Limit:** If logs show stopped at ~3000 tokens, increase `max_output_tokens` in `generator.py`
- **Network Issue:** Check internet connection

### "No crossword available" (404 error)
**Solution:** Generate crosswords manually
```bash
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new
```

### CORS errors (frontend)
**Solution:** Verify `backend/app/main.py` includes:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
```

### Frontend shows white screen
**Solution:** 
1. Open browser console (F12 or Cmd+Option+I)
2. Check for error messages
3. Verify backend is running
4. Check `npm install react-icons` was run

### Port conflicts
**Solution:** Use different port
```bash
# Backend
uvicorn app.main:app --reload --port 8001

# Frontend
npm run dev -- --port 5174
```

### Grid not 5x5
**Solution:** This is fixed with `pad_grid_to_5x5()` function in latest code. Delete old crossword files and regenerate:
```bash
rm backend/app/*.json
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new
```

### Clue numbers don't match grid
**Solution:** This is fixed in latest `SoloPlay.jsx`. Make sure you have the updated frontend code.

### Python version issues
**Solution:** 
```bash
# Check Python version
python --version

# Should be >= 3.12
# If not, create venv with correct version:
python3.13 -m venv .venv313  # macOS
py -3.13 -m venv .venv313    # Windows
```

---

## 13 — Production Deployment

### Prerequisites:
- Backend deployed to hosting service (Render, AWS, Heroku, etc.)
- GitHub repository with Actions enabled

### Steps:

1. **Deploy Backend**
   - Deploy to Render/AWS/Heroku/Railway
   - Set environment variable: `OPENAI_API_KEY`
   - Note your backend URL (e.g., `https://backend-xxx.onrender.com`)

2. **Update GitHub Actions Workflow**
   
   Edit `.github/workflows/daily-crossword.yml`:
```yaml
   - name: Generate Daily Crosswords
     run: |
       curl -X POST https://your-backend-url.com/crossword/generate-daily \
         -H "Content-Type: application/json"
```

3. **Test GitHub Actions**
   - Go to GitHub → Actions tab
   - Click "Generate Daily Crosswords"
   - Click "Run workflow"
   - Verify it completes successfully (green checkmark)

4. **Verify Schedule**
   - GitHub Actions runs at midnight UTC daily
   - Check logs after first scheduled run

5. **Monitor**
   - Check backend logs for generation success
   - Test `/crossword/solo` and `/crossword/battle` endpoints
   - Verify frontend loads crosswords

---

## 14 — GitHub Actions Testing

### Manual Trigger (Before Deployment):
```bash
# Test the endpoint GitHub Actions will call
curl -X POST https://your-backend-url.com/crossword/generate-daily
```

### After Deployment:

1. Go to GitHub repository
2. Click **Actions** tab
3. Select **Generate Daily Crosswords** workflow
4. Click **Run workflow** dropdown
5. Click **Run workflow** button
6. Watch the logs - should complete in 30-60 seconds

---

## 15 — Development Workflow

### Typical Development Session:
```bash
# Terminal 1: Backend
cd backend
source .venv313/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Frontend  
cd frontend
npm run dev

# Terminal 3: Testing
# Generate fresh crossword when needed
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new

# Test in browser at http://localhost:5173
```

### Making Changes:

1. **Backend Changes:** 
   - Edit files in `backend/app/`
   - uvicorn auto-reloads with `--reload` flag
   
2. **Frontend Changes:**
   - Edit files in `frontend/src/`
   - Vite hot-reloads automatically

3. **Generator Changes:**
   - Edit `backend/app/generator.py`
   - Restart uvicorn (Ctrl+C, then restart)
   - Test with `/test/generate-new`

---

## 16 — Contact & Support

**For issues or questions:**
- **Email:** kiannskkandan@gmail.com
- **Check logs:** Look at uvicorn console output
- **Review docs:** 
  - `TESTING_CROSSWORDS.md` for testing guide
  - `.github/workflows/daily-crossword.yml` for GitHub Actions
  - `backend/app/routes/crossword.py` for API endpoints

---

## 17 — Quick Reference

### Common Commands:
```bash
# Backend
cd backend
source .venv313/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm install react-icons
npm run dev

# Test Generation
curl -X POST http://127.0.0.1:8000/crossword/test/generate-new

# Check Files
ls backend/app/*.json
```

### Important URLs:

- **Backend:** http://127.0.0.1:8000
- **Frontend:** http://localhost:5173
- **API Docs:** http://127.0.0.1:8000/docs
- **Production Backend:** https://backend-ezw4.onrender.com
- **Production Frontend:** https://crosswars.xyz

---

**Happy puzzle generating!** 🎯