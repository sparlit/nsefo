@echo off
rem ==============================================================================
rem NSEFO Master Pro — Windows Startup Launcher
rem Usage: run_app.bat              (start web dashboard + trading engine)
rem        run_app.bat "Buy Nifty 24500 ce"  (single NLP command)
rem ==============================================================================
setlocal

rem Set PYTHONPATH to project root so python_app and dashboards are importable
set PYTHONPATH=%CD%;%PYTHONPATH%

rem Verify Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://www.python.org/downloads/
    exit /b 1
)

rem Run the Python startup
python run.py %*

endlocal