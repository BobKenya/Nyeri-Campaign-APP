@echo off
echo Starting Nyeri Campaign App...
echo API docs: http://localhost:8000/docs
echo Press Ctrl+C to stop.
echo.
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
