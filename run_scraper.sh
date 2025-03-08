#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if the virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please install venv package and try again."
        exit 1
    fi
fi

# Activate the virtual environment
source venv/bin/activate

# Install requirements if needed
if [ ! -f "venv/.requirements_installed" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        touch venv/.requirements_installed
    else
        echo "Failed to install requirements."
        exit 1
    fi
fi

# Check for Chromium if Chrome is not found
if [ -z "$CHROME_DRIVER_PATH" ]; then
    # Try to find Chrome or Chromium
    if [ -f "/usr/bin/google-chrome" ]; then
        export CHROME_DRIVER_PATH="/usr/bin/google-chrome"
        echo "Found Google Chrome at: $CHROME_DRIVER_PATH"
    elif [ -f "/usr/bin/google-chrome-stable" ]; then
        export CHROME_DRIVER_PATH="/usr/bin/google-chrome-stable"
        echo "Found Google Chrome Stable at: $CHROME_DRIVER_PATH"
    elif [ -f "/usr/bin/chromium" ]; then
        export CHROME_DRIVER_PATH="/usr/bin/chromium"
        echo "Found Chromium at: $CHROME_DRIVER_PATH"
    elif [ -f "/usr/bin/chromium-browser" ]; then
        export CHROME_DRIVER_PATH="/usr/bin/chromium-browser"
        echo "Found Chromium Browser at: $CHROME_DRIVER_PATH"
    else
        echo "Warning: Could not find Chrome or Chromium. If the script fails, please install Chrome or Chromium, or set the CHROME_DRIVER_PATH environment variable."
    fi
fi

# Run the fixed scraper with all arguments passed to this script
python threads_scraper.py "$@"

# Deactivate the virtual environment
deactivate

echo "Done!" 