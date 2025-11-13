#!/usr/bin/env python3
"""
Automation Runner for Core-Bucket Bridge
Replaces N8N workflow with native Python solution.
"""

import argparse
import json
import time
import requests
import os
from datetime import datetime
import uuid
import logging
from logging.handlers import RotatingFileHandler

# Set up logging
log_dir = "reports"
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("automation_runner")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    os.path.join(log_dir, "runner.log"), 
    maxBytes=1000000, 
    backupCount=5
)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class AutomationRunner:
    def __init__(self, config_path="config.json", api_base_url="http://localhost:8000"):
        self.config_path = config_path
        self.api_base_url = api_base_url
        self.load_config()
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded config from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Config file {self.config_path} not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            raise
            
    def send_core_update(self, module_data):
        """Send data to core update endpoint with retry logic"""
        url = f"{self.api_base_url}/core/update"
        payload = {
            "module": module_data["module"],
            "data": module_data["data"],
            "session_id": str(uuid.uuid4())
        }
        
        # Retry logic (up to 3 attempts with exponential backoff)
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    logger.info(f"Successfully sent {module_data['module']} data")
                    return response.json()
                else:
                    logger.warning(f"Attempt {attempt+1} failed with status {response.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt+1} failed with exception: {e}")
                
            if attempt < 2:  # Don't sleep after the last attempt
                # Exponential backoff: 1s, 2s, 4s
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
        logger.error(f"Failed to send {module_data['module']} data after 3 attempts")
        return None
        
    def get_bucket_status(self):
        """Get bucket status"""
        url = f"{self.api_base_url}/bucket/status"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                logger.info("Successfully retrieved bucket status")
                return response.json()
            else:
                logger.error(f"Failed to get bucket status: {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"Error getting bucket status: {e}")
            return None
            
    def execute_job(self, job):
        """Execute a single job"""
        job_name = job.get("name", "unnamed_job")
        logger.info(f"Executing job: {job_name}")
        
        results = {
            "job_name": job_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actions": []
        }
        
        # Execute triggers and actions
        for action in job.get("actions", []):
            action_type = action.get("type")
            action_result = {
                "type": action_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "success": False,
                "details": None
            }
            
            if action_type == "send_core_update":
                module_data = action.get("data", {})
                response = self.send_core_update(module_data)
                action_result["success"] = response is not None
                action_result["details"] = response
                results["actions"].append(action_result)
                
            elif action_type == "get_bucket_status":
                response = self.get_bucket_status()
                action_result["success"] = response is not None
                action_result["details"] = response
                results["actions"].append(action_result)
                
        return results
        
    def run_once(self):
        """Run all jobs once"""
        logger.info("Starting single run of automation jobs")
        run_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_file = os.path.join(log_dir, f"run_{run_timestamp}.jsonl")
        
        all_results = {
            "run_id": str(uuid.uuid4()),
            "start_time": datetime.utcnow().isoformat() + "Z",
            "jobs": []
        }
        
        for job in self.config.get("jobs", []):
            job_result = self.execute_job(job)
            all_results["jobs"].append(job_result)
            
            # Write each job result to the run file
            with open(run_file, "a") as f:
                f.write(json.dumps(job_result) + "\n")
                
        all_results["end_time"] = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Completed run. Results saved to {run_file}")
        return all_results
        
    def run_watch(self, interval_minutes=60):
        """Run jobs continuously at specified intervals"""
        logger.info(f"Starting watch mode with {interval_minutes} minute intervals")
        while True:
            try:
                self.run_once()
                logger.info(f"Sleeping for {interval_minutes} minutes")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping...")
                break
            except Exception as e:
                logger.error(f"Error in watch mode: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    parser = argparse.ArgumentParser(description="Core-Bucket Bridge Automation Runner")
    parser.add_argument(
        "--once", 
        action="store_true",
        help="Run automation jobs once and exit"
    )
    parser.add_argument(
        "--watch", 
        action="store_true",
        help="Run in watch mode (continuous execution)"
    )
    parser.add_argument(
        "--config", 
        default="config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=120,
        help="Interval in minutes for watch mode (default: 120 minutes)"
    )
    
    args = parser.parse_args()
    
    if not args.once and not args.watch:
        parser.print_help()
        return
        
    try:
        runner = AutomationRunner(config_path=args.config)
        
        if args.once:
            runner.run_once()
        elif args.watch:
            runner.run_watch(interval_minutes=args.interval)
            
    except Exception as e:
        logger.error(f"Failed to start automation runner: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())