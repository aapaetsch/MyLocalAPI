#!/bin/bash
# MyLocalAPI Development Environment Setup
# Automatically creates venv and installs dependencies

echo "MyLocalAPI - Development Environment Setup"
echo "============================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 is not installed or not in PATH"
    echo "Please install Python 3.9+ from https://python.org"
    exit 1
fi

echo "✅ Python found"
python3 --version

# Check if we're already in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "⚠️  WARNING: Already in a virtual environment ($VIRTUAL_ENV)"
    echo "Continuing anyway..."
    echo
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to create virtual environment"
        exit 1
    fi
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to install dependencies"
    echo "Try running: pip install -r requirements.txt"
    exit 1
fi

echo
echo "🎉 Development environment setup complete!"
echo
echo "Next steps:"
echo "1. Run the application: python main.py"
echo "2. Build executable: python build.py" 
echo "3. Run tests: python tests/test_unit.py"
echo "4. When done: deactivate"
echo
echo "Virtual environment is now active."
echo "To activate it again later, run: source venv/bin/activate"