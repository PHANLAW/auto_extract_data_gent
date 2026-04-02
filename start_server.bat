@echo off
echo ================================================================================
echo Starting Image Processing Agent Server
echo ================================================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo Please copy .env.example to .env and configure it.
    echo.
    pause
)

REM Start server
echo Starting server on http://localhost:8000
echo API docs available at http://localhost:8000/docs
echo Press Ctrl+C to stop
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
