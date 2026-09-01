@echo off
title TDMS Report Generator - Dependency Installer
color 0F
cls

echo.
echo ============================================================
echo   TDMS Report Generator - Python Dependency Setup
echo   Required for: tdms_report.py
echo ============================================================
echo.

:: ── Check Python is available ─────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo.
    echo  Please install Python 3.9 64-bit first:
    echo  https://www.python.org/downloads/release/python-3913/
    echo.
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

:: ── Check Python version is 3.9 ───────────────────────────────
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo     Version detected: %PYVER%
echo.

:: ── Upgrade pip ───────────────────────────────────────────────
echo [1/6] Upgrading pip...
python -m pip install --upgrade pip
echo.

:: ── Install packages ──────────────────────────────────────────
echo [2/6] Installing numpy...
python -m pip install numpy
echo.

echo [3/6] Installing matplotlib...
python -m pip install matplotlib
echo.

echo [4/6] Installing scipy...
python -m pip install scipy
echo.

echo [5/6] Installing nptdms  (TDMS file reader)...
python -m pip install nptdms
echo.

echo [6/6] Installing Pillow  (image/logo support)...
python -m pip install Pillow
echo.

:: ── Verify all packages ───────────────────────────────────────
echo ============================================================
echo   Verifying installed packages...
echo ============================================================
echo.

python -c "import numpy; print('[OK] numpy        ', numpy.__version__)"
python -c "import matplotlib; print('[OK] matplotlib   ', matplotlib.__version__)"
python -c "import scipy; print('[OK] scipy        ', scipy.__version__)"
python -c "import nptdms; print('[OK] nptdms       ', nptdms.__version__)"
python -c "import PIL; print('[OK] Pillow        ', PIL.__version__)"

echo.
echo ============================================================
echo   All dependencies installed successfully!
echo   You can now run tdms_report.py from LabVIEW.
echo ============================================================
echo.
pause
