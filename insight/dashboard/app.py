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

# Function to read security rejects log
def read_security_rejects_log():
    security_data = []
    if os.path.exists("logs/security_rejects.log"):
        with open("logs/security_rejects.log", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        # Parse the log line (timestamp - message)
                        parts = line.strip().split(' - ', 1)
                        if len(parts) == 2:
                            timestamp, message = parts
                            security_data.append({
                                "timestamp": timestamp,
                                "message": message
                            })
                    except Exception:
                        continue
    return security_data

# Function to read heartbeat log
def read_heartbeat_log():
    heartbeat_data = []
    if os.path.exists("logs/heartbeat.log"):
        with open("logs/heartbeat.log", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        heartbeat_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return heartbeat_data

# Function to read provenance chain
def read_provenance_chain():
    provenance_data = []
    if os.path.exists("logs/provenance_chain.jsonl"):
        with open("logs/provenance_chain.jsonl", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        provenance_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return provenance_data

# Function to read plugin errors
def read_plugin_errors():
    plugin_errors = []
    if os.path.exists("automation/reports/plugin_errors.log"):
        with open("automation/reports/plugin_errors.log", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        # Parse the log line (timestamp - level - message)
                        parts = line.strip().split(' - ', 2)
                        if len(parts) == 3:
                            timestamp, level, message = parts
                            plugin_errors.append({
                                "timestamp": timestamp,
                                "level": level,
                                "message": message
                            })
                    except Exception:
                        continue
    return plugin_errors

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

# Read security rejects data
security_rejects_data = read_security_rejects_log()

# Read heartbeat data
heartbeat_data = read_heartbeat_log()

# Read provenance chain data
provenance_data = read_provenance_chain()

# Read plugin errors data
plugin_errors_data = read_plugin_errors()

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

# Security Events Panel
st.subheader("🔒 Security Events")
if security_rejects_data:
    # Convert to DataFrame for better display
    df = pd.DataFrame(security_rejects_data)
    # Sort by timestamp (newest first)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp', ascending=False)
    
    # Display table
    st.dataframe(df.head(10), width='stretch')  # Show only last 10 events
else:
    st.info("No security events recorded yet.")

# Node Health View
st.subheader("🖥️ Node Health View")
st.info("Multi-node health view will be displayed here when nodes are running.")
# In a full implementation, this would show health metrics for each node

# Automation Engine Events Panel
st.subheader("⚙️ Automation Engine Events")

# Show plugin errors
st.markdown("**Plugin Errors:**")
if plugin_errors_data:
    # Convert to DataFrame for better display
    df = pd.DataFrame(plugin_errors_data)
    # Sort by timestamp (newest first)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp', ascending=False)
    
    # Display table
    st.dataframe(df.head(10), width='stretch')  # Show only last 10 events
else:
    st.info("No plugin errors recorded yet.")

# Show heartbeat events
st.markdown("**Heartbeat Events:**")
if heartbeat_data:
    # Convert to DataFrame for better display
    df = pd.DataFrame(heartbeat_data)
    # Sort by timestamp (newest first)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp', ascending=False)
    
    # Display table
    st.dataframe(df.head(10), width='stretch')  # Show only last 10 events
else:
    st.info("No heartbeat events recorded yet.")

# Show provenance chain
st.markdown("**Provenance Chain Entries:**")
if provenance_data:
    # Convert to DataFrame for better display
    df = pd.DataFrame(provenance_data)
    # Sort by timestamp (newest first)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp', ascending=False)
    
    # Display table with limited columns for better readability
    if 'hash' in df.columns and 'timestamp' in df.columns:
        display_df = df[['timestamp', 'hash']].head(10)  # Show only last 10 entries
        st.dataframe(display_df, width='stretch')
    else:
        st.dataframe(df.head(10), width='stretch')
else:
    st.info("No provenance chain entries recorded yet.")

# Sync events table
st.subheader("🔄 Sync Events History")
if flow_data:
    # Convert to DataFrame for better display
    df = pd.DataFrame(flow_data)
    # Sort by timestamp (newest first)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce')
        df = df.sort_values('timestamp', ascending=False)
    
    # Display table
    st.dataframe(df.head(20), width='stretch')  # Show only last 20 events
else:
    st.info("No sync events recorded yet. Waiting for data...")

# Auto-refresh logic
if auto_refresh:
    time.sleep(30)
    st.rerun()