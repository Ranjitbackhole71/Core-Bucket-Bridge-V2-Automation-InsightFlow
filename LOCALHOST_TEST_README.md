# Localhost Testing Guide for Core-Bucket Bridge V2

This guide explains how to test all functionality of the Core-Bucket Bridge V2 system on your local machine.

## Prerequisites

- Python 3.8 or higher
- Pip (Python package manager)
- Windows, macOS, or Linux operating system

## Quick Start

### For Windows Users:

Double-click on `run_localhost_test.bat` or run from Command Prompt:

```cmd
run_localhost_test.bat
```

### For macOS/Linux Users:

Make the script executable and run it:

```bash
chmod +x run_localhost_test.sh
./run_localhost_test.sh
```

## What the Test Does

The localhost test script will:

1. **Verify System Requirements**
   - Check if Python is installed
   - Verify required files exist
   - Install missing dependencies if needed
   - Generate RSA keypair if missing

2. **Test Core Components**
   - Start the FastAPI backend server on port 8000
   - Test API endpoints for proper functionality
   - Run the automation runner once to verify jobs execution
   - Start the Streamlit dashboard on port 8501
   - Verify log files and reports are generated

3. **Provide Access Information**
   - FastAPI Server: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Streamlit Dashboard: http://localhost:8501

## Manual Testing Options

If you prefer to test components individually:

### 1. Start the FastAPI Server
```bash
python core_bucket_bridge.py
```

### 2. Run Automation Runner
```bash
# Run once
python automation/runner.py --once

# Run in watch mode
python automation/runner.py --watch
```

### 3. Start Streamlit Dashboard
```bash
streamlit run insight/dashboard/app.py
```

## Troubleshooting

### Port Conflicts
If you see "Port already in use" errors:
- Make sure no other instances are running
- Change ports in the respective configuration files

### Missing Dependencies
If you encounter import errors:
```bash
pip install -r requirements.txt
```

### Missing RSA Keys
If security keys are missing:
```bash
python generate_keys.py
```

## Access Points After Successful Test

- **FastAPI Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Streamlit Dashboard**: http://localhost:8501

## Stopping the Services

The test script will automatically shut down all services when complete. If you started them manually, you can stop them by pressing `Ctrl+C` in each terminal window.