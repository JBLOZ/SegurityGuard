#!/bin/bash

# Define the specific Python version we want to use
PYTHON_VERSION="3.11"

echo "Checking for Python $PYTHON_VERSION..."

# Check if 'py' launcher is available (common on Windows)
if command -v py >/dev/null 2>&1; then
    echo "Found 'py' launcher. Creating virtual environment with Python $PYTHON_VERSION..."
    py -$PYTHON_VERSION -m venv venv
else
    # Fallback: check for 'python3.11' or 'python'
    if command -v python$PYTHON_VERSION >/dev/null 2>&1; then
        echo "Found python$PYTHON_VERSION. Creating virtual environment..."
        python$PYTHON_VERSION -m venv venv
    elif command -v python >/dev/null 2>&1; then
        # Check version of 'python'
        VER=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if [ "$VER" == "$PYTHON_VERSION" ]; then
             echo "Found python (version $VER). Creating virtual environment..."
             python -m venv venv
        else
             echo "Error: Python $PYTHON_VERSION is required, but 'python' is version $VER."
             echo "Please install Python $PYTHON_VERSION."
             exit 1
        fi
    else
        echo "Error: Python $PYTHON_VERSION not found."
        exit 1
    fi
fi

# Activate the virtual environment
echo "Activating virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    # Windows (Git Bash, etc.)
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # Unix-like
    source venv/bin/activate
else
    echo "Error: Could not find activation script. Virtual environment creation might have failed."
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
if [ -f "backend/requirements.txt" ]; then
    echo "Installing dependencies from backend/requirements.txt..."
    pip install -r backend/requirements.txt
else
    echo "Error: backend/requirements.txt not found!"
    exit 1
fi

echo "Installation complete!"
echo "To activate the environment in the future, run:"
echo "source venv/Scripts/activate"
