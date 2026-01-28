#!/bin/bash

echo "===================================================="
echo "Core-Bucket Bridge V2 - Localhost Functionality Test"
echo "===================================================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    echo
    exit 1
fi

# Check if required files exist
if [ ! -f "core_bucket_bridge.py" ]; then
    echo "❌ Error: core_bucket_bridge.py not found"
    echo "Please make sure you're in the correct directory"
    echo
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    echo "Please make sure you're in the correct directory"
    echo
    exit 1
fi

echo "✅ Required files found"
echo

# Check if dependencies are installed
echo "Checking if dependencies are installed..."
if ! python3 -c "import fastapi, uvicorn, streamlit, requests, pandas, jwt, cryptography" &> /dev/null; then
    echo "⚠ Warning: Some dependencies may not be installed"
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies"
        echo "Please check your internet connection and try again"
        echo
        exit 1
    fi
    echo "✅ Dependencies installed successfully"
    echo
fi

# Check if security keys exist
if [ ! -f "security/private.pem" ]; then
    echo "⚠ Warning: Private key not found"
    echo "Generating RSA keypair..."
    python3 generate_keys.py
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to generate RSA keypair"
        echo
        exit 1
    fi
    echo "✅ RSA keypair generated successfully"
    echo
fi

# Run the localhost test
echo "Starting localhost functionality test..."
echo
python3 localhost_test.py

echo
echo "Test completed."