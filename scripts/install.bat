@echo off
setlocal EnableExtensions
rem ==============================================================================
rem NSEFO Master Pro — Windows Installer (Enhanced)
rem Single-word command: install.bat  OR  setup.bat
rem
rem Arguments:
rem   install.bat              — interactive installation
rem   install.bat --non-interactive  — use existing config.json
rem   install.bat --help      — show this help
rem
rem Requirements:
rem   - Python 3.10 or higher
rem   - Rust + Cargo (optional, for the Rust performance core)
rem   - Internet connection
rem ==============================================================================

rem ─── ANSI color codes (Windows 10 build 1607+ supports VirtualTerminal) ────
for /f %%A in ('echo prompt $E') do set "ESC=%%A"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"
set "CHECK=%ESC%[92m[%ESC%[0mCHECK%ESC%[92m]%ESC%[0m"
set "CROSS=%ESC%[91m[%ESC%[0mFAIL%ESC%[91m]%ESC%[0m"
set "WARN=%ESC%[93m[%ESC%[0mWARN%ESC%[93m]%ESC%[0m"

title NSEFO Master Pro — Installation

rem ─── Parse arguments ────────────────────────────────────────────────────────
set "_NONINTERACTIVE="
set "_HELP="
for %%A in (%*) do (
    if /i "%%A"=="--non-interactive" set "_NONINTERACTIVE=1"
    if /i "%%A"=="-y" set "_NONINTERACTIVE=1"
    if /i "%%A"=="--help" set "_HELP=1"
)

if defined _HELP (
    echo NSEFO Master Pro — Windows Installer
    echo.
    echo Usage:
    echo   install.bat              — interactive installation
    echo   install.bat --non-interactive  — use existing config.json
    echo   install.bat --help       — show this help
    echo.
    echo Prerequisites:
    echo   - Python 3.10+          (https://www.python.org/downloads/)
    echo   - Rust + Cargo (opt.)  (https://rustup.rs/)
    exit /b 0
)

rem ─── Banner ─────────────────────────────────────────────────────────────────
echo.
echo %BOLD%%BLUE%  ╔══════════════════════════════════════════════╗%BOLD%%BLUE%  ║
echo  ║        NSEFO MASTER PRO — INSTALLATION           ║
echo  ║         Python + Rust Trading System            ║
echo  ╚══════════════════════════════════════════════╝%RESET%
echo.

rem ─── Step 1: Python version check ──────────────────────────────────────────
echo %BOLD%[1/5] Checking Python...%RESET%

python --version >nul 2>&1
if errorlevel 1 (
    echo %CROSS% Python not found in PATH.
    echo %RED%   Install Python 3.10+ from: https://www.python.org/downloads/%RESET%
    echo %RED%   Then re-run this installer.%RESET%
    exit /b 1
)

for /f "delims=" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
echo %CHECK% %GREEN%%PY_VERSION%%RESET% found.

rem Extract major.minor version for compatibility check
for /f "tokens=1,2 delims=." %%a in ("%PY_VERSION:Python =%") do set "PY_MAJOR=%%a" & set "PY_MINOR=%%b"
if defined PY_MINOR (
    set /a PY_VER_NUM = PY_MAJOR * 100 + PY_MINOR
) else (
    set /a PY_VER_NUM = PY_MAJOR * 100
)

if %PY_VER_NUM% LSS 310 (
    echo %CROSS% Python 3.10+ required. You have %PY_VERSION%.
    echo %RED%   Download from: https://www.python.org/downloads/%RESET%
    exit /b 1
)

rem Check pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo %CROSS% pip not available. Ensure "pip" is installed with Python.
    exit /b 1
)
echo %CHECK% pip available.

rem ─── Step 2: Install Python dependencies ────────────────────────────────────
echo.
echo %BOLD%[2/5] Installing Python dependencies...%RESET%

python -m pip install --upgrade pip -q >nul 2>&1
if errorlevel 1 (
    echo %WARN% pip upgrade skipped (may already be current).
)

python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo %WARN% Initial pip install had issues. Retrying with verbose output...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo %CROSS% pip install failed. Check your internet connection.
        exit /b 1
    )
)
echo %CHECK% Python packages installed.

rem ─── Step 2b: Playwright browser (for browser-based auth) ──────────────────
echo.
echo %BOLD%[2b/5] Installing Playwright Chromium (for broker login automation)...%RESET%

python -m playwright install --with-deps chromium >nul 2>&1
if errorlevel 1 (
    echo %WARN% Playwright install skipped. Run manually if you need browser login:
    echo %WARN%   python -m playwright install --with-deps chromium
) else (
    echo %CHECK% Playwright Chromium installed.
)

rem ─── Step 3: Build Rust core (optional) ────────────────────────────────────
echo.
echo %BOLD%[3/5] Building Rust Performance Core...%RESET%

where cargo >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%   Rust (cargo) not found — skipping Rust core build.
    echo %YELLOW%   Install from https://rustup.rs to enable the performance core.
    echo %YELLOW%   After installing Rust, re-run: install.bat
    set "RUST_FOUND=0"
) else (
    echo %CHECK% Rust found.

    for /f "delims=" %%v in ('cargo --version 2^>^&1') do set "RUST_VERSION=%%v"
    echo    %RUST_VERSION%

    cd nsefo_core
    set "PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1"

    echo    Compiling (this may take 3-5 minutes on first run)...
    python -m maturin build --release 2> ..\maturin_err.txt
    if errorlevel 1 (
        echo %WARN% Rust build failed. The application will still run (Python fallback).
        echo %WARN% Fix: install Rust from https://rustup.rs then re-run install.bat
        type nul > nul
        more maturin_err.txt 2>nul | findstr /i "error:" 2>nul | findstr /v "Compiling" 2>nul
    ) else (
        for /f "delims=" %%w in ('dir /b target\wheels\*.whl 2^>nul') do (
            echo    Wheel: %%w
            python -m pip install "target\wheels\%%w" --force-reinstall -q 2>nul
            if errorlevel 1 (
                echo %CROSS% Wheel install failed. Try manually:
                echo        python -m pip install "target\wheels\%%w" --force-reinstall
            ) else (
                echo %CHECK% nsefo_core installed in site-packages.
            )
        )
    )
    cd ..

    rem Clean up temp file
    if exist maturin_err.txt del maturin_err.txt >nul 2>&1
)

rem ─── Step 4: Configuration wizard ─────────────────────────────────────────
echo.
echo %BOLD%[4/5] Configuration Wizard%RESET%

if defined _NONINTERACTIVE (
    if exist config.json (
        echo    Skipping config wizard (non-interactive, existing config.json used).
    ) else (
        echo %WARN% No config.json found. Running wizard in interactive mode...
        python install.py
    )
) else (
    python install.py
    if errorlevel 1 (
        echo %CROSS% Configuration wizard failed.
        exit /b 1
    )
)

rem ─── Step 5: Connectivity verification ────────────────────────────────────
echo.
echo %BOLD%[5/5] Connectivity Check%RESET%

python -c "import sys; sys.path.insert(0,'.'); from python_app.broker.session_manager import SessionManager; sm=SessionManager(); b=sm.get_broker(); print('OK' if b else 'FAIL')" 2>nul
if errorlevel 1 (
    echo %WARN% Connectivity check skipped (run: nsefo.bat to verify manually).
) else (
    for /f %%r in ('python -c "import sys; sys.path.insert(0,'.'); from python_app.broker.session_manager import SessionManager; sm=SessionManager(); b=sm.get_broker(); print('OK' if b else 'FAIL')" 2^>^&1') do set "CONN_RESULT=%%r"
    if /i "%CONN_RESULT%"=="OK" (
        echo %CHECK% Broker connectivity verified.
    ) else (
        echo %WARN% Broker auth failed. Run: python run.py --setup   to reconfigure.
    )
)

rem ─── Done ──────────────────────────────────────────────────────────────────
echo.
echo %BOLD%%GREEN%  ╔══════════════════════════════════════════════╗%RESET%
echo %BOLD%%GREEN%  ║        INSTALLATION COMPLETE                 ║%RESET%
echo %BOLD%%GREEN%  ╚══════════════════════════════════════════════╝%RESET%
echo.
echo  To start the application:
echo   %BOLD%nsefo.bat%RESET%   — single-word command
echo   Or: %BOLD%python run.py%RESET%
echo.
if not defined RUST_FOUND (
    echo  NOTE: Rust core not built. High-performance indicators unavailable.
    echo        Install Rust from https://rustup.rs then re-run install.bat
    echo.
)

endlocal
exit /b 0