@echo off
cd /d "%~dp0backend"
if not exist .env (
  copy .env.example .env >nul
  echo A new .env file was created. Paste your GROQ_API_KEY, TAVILY_API_KEY and JWT_SECRET, save, then close Notepad.
  notepad .env
)
if not exist venv python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
echo.
echo Backend starting at http://localhost:8000  (check http://localhost:8000/health)
venv\Scripts\python -m uvicorn main:app --reload
pause
