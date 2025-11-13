import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os
import time
import requests

# Page configuration
st.set_page_config(
    page_title="InsightFlow Dashboard",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 InsightFlow Dashboard")
st.markdown("Real-time monitoring of Core-Bucket data synchronization")

# Function to read flow log
def read_flow_log():
    flow_data = []
    if os.path.exists("insight/flow.log"):
        with open("insight/flow.log", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        flow_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return flow_data

# Function to read metrics log
def read_metrics_log():
    metrics_data = []
    if os.path.exists("logs/metrics.jsonl"):
        with open("logs/metrics.jsonl", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        metrics_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return metrics_data

# Function to get health data from API
def get_health_data():
    try:
        response = requests.get("http://localhost:8000/core/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# Function to calculate metrics
def calculate_metrics(flow_data, metrics_data):
    if not flow_data:
        return 0, 0, 0, 0, {}, ""
    
    # Calculate average latency from flow data
    latencies = [entry.get("latency_ms", 0) for entry in flow_data if "latency_ms" in entry]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # Calculate success rate (assuming all flow entries are successes)
    total_events = len(flow_data)
    success_rate = 100.0  # Simplified for now
    
    # Error count (simplified)
    error_count = 0
    
    # Queue depth (simplified)
    queue_depth = 0
    
    # Last sync time per module
    last_sync_times = {}
    for entry in flow_data:
        module = entry.get("module", "unknown")
        timestamp = entry.get("timestamp", "")
        if module not in last_sync_times or timestamp > last_sync_times[module]:
            last_sync_times[module] = timestamp
    
    # Overall last sync time
    overall_last_sync = max([entry.get("timestamp", "") for entry in flow_data]) if flow_data else ""
    
    return success_rate, avg_latency, error_count, queue_depth, last_sync_times, overall_last_sync

# Auto-refresh functionality
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

# Refresh button
if st.button("🔄 Refresh Data"):
    st.session_state.refresh_counter += 1

# Auto-refresh checkbox
auto_refresh = st.checkbox("Auto-refresh every 30 seconds", value=True)

# Create columns for metrics
col1, col2, col3, col4 = st.columns(4)

# Get health data from API
health_data = get_health_data()

# Read flow data
flow_data = read_flow_log()

# Read metrics data
metrics_data = read_metrics_log()

# Calculate metrics
success_rate, avg_latency, error_count, queue_depth, last_sync_times, overall_last_sync = calculate_metrics(flow_data, metrics_data)

# Display metrics
with col1:
    # Sync Success %
    success_rate_display = health_data["status"] if health_data else "Unknown"
    status_color = "🟢" if success_rate_display == "ok" else "🔴"
    st.metric("Status", f"{status_color} {success_rate_display}")

with col2:
    # Avg Latency
    avg_latency_display = f"{health_data['avg_latency_ms_24h']:.2f} ms" if health_data else "0.00 ms"
    st.metric("Avg Latency (24h)", avg_latency_display)

with col3:
    # Error Count
    error_count_display = health_data["error_count_24h"] if health_data else 0
    st.metric("Errors (24h)", error_count_display)

with col4:
    # Queue Depth
    queue_depth_display = health_data["pending_queue"] if health_data else 0
    st.metric("Queue Depth", queue_depth_display)

# Last sync time per module
st.subheader("Last Sync Time by Module")
if last_sync_times:
    module_times_df = pd.DataFrame(list(last_sync_times.items()))
    module_times_df.columns = ["Module", "Last Sync Time"]
    st.table(module_times_df)
else:
    st.info("No sync events recorded yet.")

# Sync events table
st.subheader("Sync Events History")
if flow_data:
    # Convert to DataFrame for better display
    df = pd.DataFrame(flow_data)
    # Sort by timestamp (newest first)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce')
        df = df.sort_values('timestamp', ascending=False)
    
    # Display table
    st.dataframe(df, width='stretch')
else:
    st.info("No sync events recorded yet. Waiting for data...")

# Auto-refresh logic
if auto_refresh:
    time.sleep(30)
    st.rerun()