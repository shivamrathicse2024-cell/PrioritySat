@echo off
setlocal
cd /d "%~dp0backend"
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if errorlevel 1 (
  echo Installing backend dependencies. Internet may be required on first setup...
  pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Check Python and internet connectivity.
    pause
    exit /b 1
  )
)
echo Starting PrioritySat API at http://127.0.0.1:8000
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
