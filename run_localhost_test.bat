@echo off
echo ====================================================
echo Core-Bucket Bridge V2 - Localhost Functionality Test
echo ====================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "core_bucket_bridge.py" (
    echo ❌ Error: core_bucket_bridge.py not found
    echo Please make sure you're in the correct directory
    echo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ❌ Error: requirements.txt not found
    echo Please make sure you're in the correct directory
    echo.
    pause
    exit /b 1
)

echo ✅ Required files found
echo.

REM Check if dependencies are installed
echo Checking if dependencies are installed...
python -c "import fastapi, uvicorn, streamlit, requests, pandas, jwt, cryptography" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠ Warning: Some dependencies may not be installed
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Error: Failed to install dependencies
        echo Please check your internet connection and try again
        echo.
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed successfully
    echo.
)

REM Check if security keys exist
if not exist "security\private.pem" (
    echo ⚠ Warning: Private key not found
    echo Generating RSA keypair...
    python generate_keys.py
    if %errorlevel% neq 0 (
        echo ❌ Error: Failed to generate RSA keypair
        echo.
        pause
        exit /b 1
    )
    echo ✅ RSA keypair generated successfully
    echo.
)

REM Run the localhost test
echo Starting localhost functionality test...
echo.
python localhost_test.py

echo.
echo Test completed.
echo.
pause