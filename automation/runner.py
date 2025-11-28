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
from datetime import datetime, timedelta
import uuid
import logging
from logging.handlers import RotatingFileHandler
import importlib.util
import sys
import jwt
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

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
        self.load_private_key()
        
    def load_private_key(self):
        """Load private key for signing requests"""
        try:
            with open("security/private.pem", "rb") as key_file:
                self.private_key = serialization.load_pem_private_key(key_file.read(), password=None)
            logger.info("Loaded private key for signing")
        except Exception as e:
            logger.error(f"Error loading private key: {e}")
            self.private_key = None
            
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
            
    def sign_payload(self, payload):
        """Sign a payload with RSA private key"""
        if not self.private_key:
            logger.error("Private key not loaded")
            return None
            
        try:
            payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
            signature = self.private_key.sign(
                payload_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"Error signing payload: {e}")
            return None
            
    def create_jwt_token(self, roles=["module"]):
        """Create a JWT token for requests"""
        try:
            payload = {
                "iss": "core-bucket-bridge",
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
                "roles": roles
            }
            token = jwt.encode(payload, "secret", algorithm="HS256")
            return f"Bearer {token}"
        except Exception as e:
            logger.error(f"Error creating JWT token: {e}")
            return None
            
    def send_secure_request(self, endpoint, payload, roles=["module"]):
        """Send a secure request with signature and JWT token"""
        # Sign the payload
        signature = self.sign_payload(payload)
        if not signature:
            logger.error(f"Failed to sign payload for {endpoint}")
            return None
            
        # Create JWT token
        token = self.create_jwt_token(roles)
        if not token:
            logger.error(f"Failed to create JWT token for {endpoint}")
            return None
            
        # Create secure payload
        secure_payload = {
            "payload": payload,
            "signature": signature,
            "nonce": str(uuid.uuid4())  # Unique nonce for each request
        }
        
        # Send request
        url = f"{self.api_base_url}{endpoint}"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        
        # Retry logic (up to 3 attempts with exponential backoff)
        for attempt in range(3):
            try:
                response = requests.post(url, json=secure_payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    logger.info(f"Successfully sent secure request to {endpoint}")
                    return response.json()
                else:
                    logger.warning(f"Attempt {attempt+1} failed with status {response.status_code} for {endpoint}")
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt+1} failed with exception for {endpoint}: {e}")
                
            if attempt < 2:  # Don't sleep after the last attempt
                # Exponential backoff: 1s, 2s, 4s
                sleep_time = 2 ** attempt
                logger.info(f"Retrying {endpoint} in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
        logger.error(f"Failed to send secure request to {endpoint} after 3 attempts")
        return None
        
    def send_core_update(self, module_data):
        """Send data to core update endpoint with signature and JWT"""
        payload = {
            "module": module_data["module"],
            "data": module_data["data"],
            "session_id": str(uuid.uuid4())
        }
        
        return self.send_secure_request("/core/update", payload, ["module"])
        
    def send_heartbeat(self, heartbeat_data):
        """Send heartbeat to core heartbeat endpoint with signature and JWT"""
        payload = {
            "module": heartbeat_data["module"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": heartbeat_data.get("status", "alive"),
            "metrics": heartbeat_data.get("metrics", {})
        }
        
        return self.send_secure_request("/core/heartbeat", payload, ["module"])
        
    def get_bucket_status(self):
        """Get bucket status with JWT authentication"""
        url = f"{self.api_base_url}/bucket/status"
        
        # Create JWT token
        token = self.create_jwt_token(["module"])
        if not token:
            logger.error("Failed to create JWT token for bucket status")
            return None
            
        headers = {
            "Authorization": token
        }
        
        # Retry logic (up to 3 attempts with exponential backoff)
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    logger.info("Successfully retrieved bucket status")
                    return response.json()
                else:
                    logger.warning(f"Attempt {attempt+1} failed with status {response.status_code} for bucket status")
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt+1} failed with exception for bucket status: {e}")
                
            if attempt < 2:  # Don't sleep after the last attempt
                # Exponential backoff: 1s, 2s, 4s
                sleep_time = 2 ** attempt
                logger.info(f"Retrying bucket status in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
        logger.error("Failed to get bucket status after 3 attempts")
        return None
            
    def load_plugin(self, plugin_name):
        """Dynamically load a plugin"""
        try:
            plugin_path = os.path.join("automation", "plugins", f"{plugin_name}.py")
            if not os.path.exists(plugin_path):
                logger.error(f"Plugin {plugin_name} not found at {plugin_path}")
                return None
                
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return None
            
    def execute_plugin(self, plugin_name):
        """Execute a plugin and log results"""
        plugin = self.load_plugin(plugin_name)
        if not plugin:
            return None
            
        try:
            result = plugin.run()
            logger.info(f"Plugin {plugin_name} executed successfully")
            
            # Log to engine log
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "plugin": plugin_name,
                "event": "plugin_executed",
                "result": result
            }
            
            engine_log_path = os.path.join(log_dir, "engine.log")
            with open(engine_log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
            return result
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_name}: {e}")
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
                
            elif action_type == "send_heartbeat":
                heartbeat_data = action.get("data", {})
                response = self.send_heartbeat(heartbeat_data)
                action_result["success"] = response is not None
                action_result["details"] = response
                results["actions"].append(action_result)
                
            elif action_type == "get_bucket_status":
                response = self.get_bucket_status()
                action_result["success"] = response is not None
                action_result["details"] = response
                results["actions"].append(action_result)
                
            elif action_type == "run_plugin":
                plugin_name = action.get("plugin_name")
                if plugin_name:
                    response = self.execute_plugin(plugin_name)
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