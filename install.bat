@echo off
setlocal

REM Define Python version
set PYTHON_VERSION=3.11

echo Checking for Python %PYTHON_VERSION%...

REM Check if py launcher is available
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Found 'py' launcher. Creating virtual environment with Python %PYTHON_VERSION%...
    py -%PYTHON_VERSION% -m venv venv
) else (
    echo 'py' launcher not found. Checking for python...
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        python -c "import sys; exit(0) if sys.version_info.major == 3 and sys.version_info.minor == 11 else exit(1)"
        if %ERRORLEVEL% EQU 0 (
            echo Found Python 3.11. Creating virtual environment...
            python -m venv venv
        ) else (
            echo Error: Python 3.11 is required but the default 'python' is not 3.11.
            echo Please install Python 3.11 or use the 'py' launcher.
            pause
            exit /b 1
        )
    ) else (
        echo Error: Python not found.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
if exist "backend\requirements.txt" (
    echo Installing dependencies from backend\requirements.txt...
    pip install -r backend\requirements.txt
) else (
    echo Error: backend\requirements.txt not found!
    pause
    exit /b 1
)

echo Installation complete!
echo To activate the environment in the future, run:
echo venv\Scripts\activate
pause
