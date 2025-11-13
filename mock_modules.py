import requests
import time
import json
from datetime import datetime
import uuid
import threading

# Mock modules data
MOCK_MODULES = {
    "education": {
        "course_id": "CS101",
        "course_name": "Introduction to Computer Science",
        "students_enrolled": 150,
        "instructor": "Dr. Smith"
    },
    "finance": {
        "account_id": "ACC123456",
        "balance": 25000.75,
        "currency": "USD",
        "last_transaction": "2025-10-15T14:30:00Z"
    },
    "creative": {
        "project_id": "PRJ789",
        "project_name": "Website Redesign",
        "status": "in_progress",
        "deadline": "2025-12-01T00:00:00Z"
    },
    "robotics": {
        "robot_id": "RBT001",
        "status": "operational",
        "battery_level": 87.5,
        "last_maintenance": "2025-10-10T09:15:00Z"
    }
}

def send_mock_data(module_name, data, api_url="http://localhost:8000"):
    """
    Send mock data to the core update endpoint
    """
    url = f"{api_url}/core/update"
    payload = {
        "module": module_name,
        "data": data,
        "session_id": str(uuid.uuid4())
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Successfully sent {module_name} data: {response.json()}")
        else:
            print(f"Failed to send {module_name} data: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending {module_name} data: {str(e)}")

def run_mock_modules():
    """
    Run mock modules to send sample payloads every few minutes
    """
    print("Starting mock modules...")
    while True:
        for module_name, data in MOCK_MODULES.items():
            send_mock_data(module_name, data)
            time.sleep(2)  # Wait 2 seconds between each module
        print(f"All modules sent data at {datetime.now().isoformat()}")
        time.sleep(30)  # Wait 30 seconds before next cycle

if __name__ == "__main__":
    run_mock_modules()