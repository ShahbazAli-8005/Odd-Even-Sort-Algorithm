@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   Odd-Even Sort Visualizer - Startup Script
echo ===================================================

:: Check for python
set "PYTHON_CMD="
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
) else (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=py"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python was not found on your system.
    echo Please download and install Python from https://www.python.org/
    echo Make sure to check the option "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [INFO] Found Python: %PYTHON_CMD%

:: Check if .venv folder exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment in .venv...
    %PYTHON_CMD% -m venv .venv
    if !errorlevel! neq 0 (
        echo [WARNING] Failed to create virtual environment.
        echo Attempting to install dependencies globally/user-level...
        %PYTHON_CMD% -m pip install -r requirements.txt --user
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to install dependencies.
            pause
            exit /b 1
        )
        goto RUN_GLOBAL
    )
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo [WARNING] Failed to activate virtual environment.
    echo Running with global Python installation...
    goto RUN_GLOBAL
)

:: Install/update dependencies
echo [INFO] Verifying and installing dependencies...
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install dependencies in virtual environment.
    pause
    exit /b 1
)

:: Run program
echo [INFO] Starting Odd-Even Sort Visualizer...
python main.py
goto END

:RUN_GLOBAL
echo [INFO] Running with global python and dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt
%PYTHON_CMD% main.py
goto END

:END
echo.
echo [INFO] Program finished.
pause
