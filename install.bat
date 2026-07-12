@echo off
rem ==============================================================================
rem NSEFO Master Pro — Windows Installer
rem Usage: install.bat              (interactive setup)
rem        install.bat --setup     (force configuration wizard)
rem        install.bat --non-interactive  (use existing config.json)
rem ==============================================================================
setlocal

echo.
echo ========================================
echo   NSEFO MASTER PRO — INSTALLATION
echo ========================================
echo.

rem Step 1: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from: https://www.python.org/downloads/
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
echo [1/4] Python found: %PY_VERSION%

rem Step 2: Install dependencies
echo.
echo [2/4] Installing Python dependencies...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [WARNING] pip install had issues. Trying with upgrade...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)
echo [2/4] Dependencies installed.

rem Step 2b: Install Playwright browsers (required for browser_login.py)
python -m playwright install --with-deps chromium 2>nul
if not errorlevel 1 (
    echo [2b/4] Playwright Chromium installed.
) else (
    echo [2b/4] Playwright browser install skipped — run manually: python -m playwright install --with-deps
)

rem Step 3: Compile Rust core (if Rust is available)
echo.
where cargo >nul 2>&1
if not errorlevel 1 (
    echo [3/4] Compiling Rust Performance Core...
    cd nsefo_core
    set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
    python -m maturin build --release
    if errorlevel 1 (
        echo [WARNING] Rust build failed. Install Rust from https://rustup.rs
    ) else (
        for /f "delims=" %%w in ('dir /b target\wheels\*.whl 2^>nul') do (
            echo [3/4] Installing wheel: %%w
            python -m pip install "target\wheels\%%w" --force-reinstall -q
        )
    )
    cd ..
    echo [3/4] Rust core compiled.
) else (
    echo [3/4] Rust not found — skipping Rust core build.
    echo Install Rust from https://rustup.rs to enable the high-performance core.
)

rem Step 4: Run configuration
echo.
echo [4/4] Running configuration...
python install.py %*

echo.
echo ========================================
echo   INSTALLATION COMPLETE
echo ========================================
echo.
echo   Next step — configure and start:
echo   Run: nsefo.bat
echo   Or:  python run.py
echo.

endlocal