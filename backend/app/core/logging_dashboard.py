# File: app/core/logging_dashboard.py
"""
Logging Dashboard and Debug Utilities
Provides endpoints and utilities for monitoring and debugging the logging system
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from threading import Lock
import asyncio

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from .logging_config import (
    get_logger_tree, 
    get_request_context,
    PROMETHEUS_AVAILABLE,
    OPENTELEMETRY_AVAILABLE
)

if PROMETHEUS_AVAILABLE:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Structured log entry for in-memory storage"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    extra_data: Dict[str, Any]
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class LogBuffer:
    """Thread-safe circular buffer for storing recent log entries"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = Lock()
        self.stats = defaultdict(int)
        
    def add_entry(self, entry: LogEntry):
        """Add a log entry to the buffer"""
        with self.lock:
            self.buffer.append(entry)
            self.stats[entry.level] += 1
            self.stats['total'] += 1
            
    def get_recent_entries(self, limit: int = 100, level_filter: str = None) -> List[LogEntry]:
        """Get recent log entries with optional filtering"""
        with self.lock:
            entries = list(self.buffer)
            
        if level_filter:
            entries = [e for e in entries if e.level.lower() == level_filter.lower()]
            
        # Return the most recent entries first (reverse order)
        return list(reversed(entries[-limit:]))
    
    def get_stats(self) -> Dict[str, int]:
        """Get logging statistics"""
        with self.lock:
            return dict(self.stats)
    
    def clear(self):
        """Clear the buffer"""
        with self.lock:
            self.buffer.clear()
            self.stats.clear()


class LogCapture(logging.Handler):
    """Custom logging handler that captures logs for the dashboard"""
    
    def __init__(self, log_buffer: LogBuffer):
        super().__init__()
        self.log_buffer = log_buffer
        
    def emit(self, record):
        """Emit a log record to the buffer"""
        try:
            # Extract extra data
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                              'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process', 'getMessage',
                              'message']:
                    extra_data[key] = str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
            
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created).isoformat(),
                level=record.levelname,
                logger_name=record.name,
                message=record.getMessage(),
                extra_data=extra_data,
                request_id=getattr(record, 'request_id', None),
                user_id=getattr(record, 'user_id', None),
                session_id=getattr(record, 'session_id', None)
            )
            
            self.log_buffer.add_entry(entry)
            
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Error in LogCapture: {e}")


# Global log buffer instance
log_buffer = LogBuffer(max_size=2000)


class LogDashboardResponse(BaseModel):
    """Response model for log dashboard data"""
    recent_logs: List[Dict[str, Any]]
    stats: Dict[str, int]
    logger_tree: List[Dict[str, Any]]
    system_info: Dict[str, Any]


class LogFilterRequest(BaseModel):
    """Request model for log filtering"""
    level: Optional[str] = None
    logger_name: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    since_timestamp: Optional[str] = None
    limit: int = 100


def setup_log_capture():
    """Setup log capture for the dashboard"""
    capture_handler = LogCapture(log_buffer)
    capture_handler.setLevel(logging.DEBUG)
    
    # Add to root logger to capture all logs
    root_logger = logging.getLogger()
    root_logger.addHandler(capture_handler)
    
    logger.info("🔧 Log capture initialized for dashboard")


def get_system_info() -> Dict[str, Any]:
    """Get current system information"""
    import platform
    import psutil
    import os
    
    try:
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'process_id': os.getpid(),
            'uptime_seconds': time.time() - psutil.Process().create_time(),
            'active_threads': psutil.Process().num_threads(),
        }
    except Exception as e:
        return {'error': f"Failed to get system info: {e}"}


def filter_logs(entries: List[LogEntry], filters: LogFilterRequest) -> List[LogEntry]:
    """Filter log entries based on criteria"""
    filtered = entries
    
    if filters.level:
        filtered = [e for e in filtered if e.level.lower() == filters.level.lower()]
    
    if filters.logger_name:
        filtered = [e for e in filtered if filters.logger_name in e.logger_name]
    
    if filters.request_id:
        filtered = [e for e in filtered if e.request_id == filters.request_id]
    
    if filters.user_id:
        filtered = [e for e in filtered if e.user_id == filters.user_id]
    
    if filters.since_timestamp:
        try:
            since_dt = datetime.fromisoformat(filters.since_timestamp.replace('Z', '+00:00'))
            filtered = [e for e in filtered 
                       if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')) >= since_dt]
        except ValueError:
            pass  # Invalid timestamp format, skip filter
    
    # Return the most recent entries first (reverse order)
    return list(reversed(filtered[-filters.limit:]))


def create_dashboard_routes(app: FastAPI):
    """Create logging dashboard routes"""
    
    @app.get("/admin/logs/dashboard", response_class=HTMLResponse)
    async def logs_dashboard():
        """Serve the logging dashboard HTML page"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Infinitum AI Agent - Logging Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1400px; margin: 0 auto; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .stat-value { font-size: 2em; font-weight: bold; color: #3498db; }
                .stat-label { color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }
                .logs-container { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .log-entry { padding: 10px; border-bottom: 1px solid #ecf0f1; font-family: 'Courier New', monospace; font-size: 0.9em; }
                .log-entry:hover { background: #f8f9fa; }
                .log-level { padding: 3px 8px; border-radius: 3px; color: white; font-weight: bold; margin-right: 10px; }
                .level-DEBUG { background: #6c757d; }
                .level-INFO { background: #007bff; }
                .level-WARNING { background: #ffc107; color: black; }
                .level-ERROR { background: #dc3545; }
                .level-CRITICAL { background: #6f42c1; }
                .timestamp { color: #6c757d; margin-right: 10px; }
                .logger-name { color: #28a745; margin-right: 10px; }
                .message { color: #212529; }
                .extra-data { 
                    margin-top: 5px; 
                    color: #6c757d; 
                    font-size: 0.8em; 
                    background: #f8f9fa;
                    padding: 8px;
                    border-radius: 4px;
                    border-left: 3px solid #dee2e6;
                    max-height: 200px;
                    overflow-y: auto;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
                .json-container { 
                    background: #f8f9fa; 
                    border-radius: 4px; 
                    padding: 8px; 
                    margin: 4px 0;
                }
                .json-key { color: #d63384; font-weight: bold; }
                .json-string { color: #198754; }
                .json-number { color: #0d6efd; }
                .json-boolean { color: #fd7e14; }
                .json-null { color: #6c757d; font-style: italic; }
                .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
                .filters { background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .filter-input { margin: 5px; padding: 8px; border: 1px solid #ced4da; border-radius: 3px; }
                .loading { text-align: center; padding: 20px; color: #6c757d; }
                .error { color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 5px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 Infinitum AI Agent - Logging Dashboard</h1>
                    <p>Real-time monitoring and debugging interface</p>
                </div>
                
                <div class="stats-grid" id="stats-grid">
                    <div class="loading">Loading statistics...</div>
                </div>
                
                <div class="filters">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 10px;">
                        <label>Level: 
                            <select id="level-filter" class="filter-input">
                                <option value="">All Levels</option>
                                <option value="DEBUG">🐛 DEBUG</option>
                                <option value="INFO">ℹ️ INFO</option>
                                <option value="WARNING">⚠️ WARNING</option>
                                <option value="ERROR">❌ ERROR</option>
                                <option value="CRITICAL">🚨 CRITICAL</option>
                            </select>
                        </label>
                        
                        <label>Logger: 
                            <input type="text" id="logger-filter" class="filter-input" placeholder="🏷️ Filter by logger name">
                        </label>
                        
                        <label>Request ID: 
                            <input type="text" id="request-filter" class="filter-input" placeholder="🔗 Filter by request ID">
                        </label>
                        
                        <label>Message Search: 
                            <input type="text" id="message-filter" class="filter-input" placeholder="🔍 Search in messages">
                        </label>
                        
                        <label>Limit: 
                            <input type="number" id="limit-filter" class="filter-input" value="100" min="10" max="1000">
                        </label>
                        
                        <label>Auto Refresh: 
                            <input type="checkbox" id="auto-refresh" checked> 
                            <span style="font-size: 0.9em;">Every 10s</span>
                        </label>
                    </div>
                    
                    <div style="text-align: center;">
                        <button onclick="refreshLogs()" class="refresh-btn">🔄 Refresh Now</button>
                        <button onclick="clearLogs()" class="refresh-btn" style="background: #dc3545;">🗑️ Clear Buffer</button>
                        <button onclick="exportLogs()" class="refresh-btn" style="background: #28a745;">📥 Export JSON</button>
                        <button onclick="toggleCompactView()" class="refresh-btn" style="background: #6f42c1;" id="compact-btn">📱 Compact View</button>
                    </div>
                </div>
                
                <div class="logs-container">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3>Recent Log Entries</h3>
                        <div id="logs-status" style="color: #6c757d; font-size: 0.9em;">Loading...</div>
                    </div>
                    <div id="logs-content">
                        <div class="loading">Loading logs...</div>
                    </div>
                </div>
            </div>
            
            <script>
                let autoRefresh = true;
                
                async function fetchDashboardData() {
                    console.log('🔍 Fetching dashboard data...');
                    try {
                        const response = await fetch('/admin/logs/api');
                        console.log('📡 Response received:', response.status);
                        const data = await response.json();
                        console.log('📊 Data parsed:', data);
                        console.log('📝 Logs count:', data.recent_logs ? data.recent_logs.length : 'No recent_logs');
                        
                        updateStats(data.stats);
                        updateLogs(data.recent_logs);
                        
                        // Update status
                        const statusElement = document.getElementById('logs-status');
                        if (statusElement) {
                            statusElement.textContent = `Showing ${data.recent_logs.length} logs`;
                        }
                    } catch (error) {
                        console.error('❌ Error fetching dashboard data:', error);
                        document.getElementById('logs-content').innerHTML = '<div class="error">Error loading data: ' + error.message + '</div>';
                    }
                }
                
                function updateStats(stats) {
                    const statsGrid = document.getElementById('stats-grid');
                    const statCards = Object.entries(stats).map(([key, value]) => 
                        `<div class="stat-card">
                            <div class="stat-value">${value}</div>
                            <div class="stat-label">${key.replace('_', ' ').toUpperCase()}</div>
                        </div>`
                    ).join('');
                    statsGrid.innerHTML = statCards;
                }
                
                function formatJson(obj, indent = 0) {
                    if (obj === null) return '<span class="json-null">null</span>';
                    if (typeof obj === 'string') return `<span class="json-string">"${obj}"</span>`;
                    if (typeof obj === 'number') return `<span class="json-number">${obj}</span>`;
                    if (typeof obj === 'boolean') return `<span class="json-boolean">${obj}</span>`;
                    
                    if (Array.isArray(obj)) {
                        if (obj.length === 0) return '[]';
                        const items = obj.map(item => '  '.repeat(indent + 1) + formatJson(item, indent + 1));
                        return '[\\n' + items.join(',\\n') + '\\n' + '  '.repeat(indent) + ']';
                    }
                    
                    if (typeof obj === 'object') {
                        const keys = Object.keys(obj);
                        if (keys.length === 0) return '{}';
                        const items = keys.map(key => 
                            '  '.repeat(indent + 1) + 
                            `<span class="json-key">"${key}"</span>: ${formatJson(obj[key], indent + 1)}`
                        );
                        return '{\\n' + items.join(',\\n') + '\\n' + '  '.repeat(indent) + '}';
                    }
                    
                    return String(obj);
                }

                function updateLogs(logs) {
                    console.log('📋 updateLogs called with:', logs);
                    const logsContent = document.getElementById('logs-content');
                    console.log('📦 logsContent element:', logsContent);
                    
                    if (!logs || logs.length === 0) {
                        console.warn('⚠️ No logs available');
                        logsContent.innerHTML = '<div class="loading">No logs available</div>';
                        return;
                    }
                    
                    const logEntries = logs.map(log => {
                        let extraData = '';
                        if (Object.keys(log.extra_data).length > 0) {
                            const formattedJson = formatJson(log.extra_data);
                            extraData = `<div class="extra-data">${formattedJson}</div>`;
                        }
                        
                        // Truncate very long messages
                        let displayMessage = log.message;
                        if (displayMessage.length > 200) {
                            displayMessage = displayMessage.substring(0, 200) + '...';
                        }
                        
                        return `<div class="log-entry">
                            <span class="log-level level-${log.level}">${log.level}</span>
                            <span class="timestamp">${new Date(log.timestamp).toLocaleString()}</span>
                            <span class="logger-name">${log.logger_name}</span>
                            <span class="message" title="${log.message.replace(/"/g, '&quot;')}">${displayMessage}</span>
                            ${extraData}
                        </div>`;
                    }).join('');
                    
                    console.log('🎨 Setting innerHTML with', logEntries.length, 'characters');
                    logsContent.innerHTML = logEntries;
                    console.log('✅ HTML updated successfully');
                }
                
                let compactMode = false;
                
                async function refreshLogs() {
                    const filters = {
                        level: document.getElementById('level-filter').value,
                        logger_name: document.getElementById('logger-filter').value,
                        request_id: document.getElementById('request-filter').value,
                        limit: parseInt(document.getElementById('limit-filter').value)
                    };
                    
                    // Add message search filter
                    const messageSearch = document.getElementById('message-filter').value;
                    
                    try {
                        const response = await fetch('/admin/logs/filter', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(filters)
                        });
                        const data = await response.json();
                        
                        // Client-side message filtering
                        let filteredLogs = data.logs;
                        if (messageSearch) {
                            filteredLogs = data.logs.filter(log => 
                                log.message.toLowerCase().includes(messageSearch.toLowerCase())
                            );
                        }
                        
                        updateLogs(filteredLogs);
                        
                        // Update status
                        const statusText = `Showing ${filteredLogs.length} of ${data.total_available} logs`;
                        const statusElement = document.getElementById('logs-status');
                        if (statusElement) {
                            statusElement.textContent = statusText;
                        }
                        
                    } catch (error) {
                        document.getElementById('logs-content').innerHTML = '<div class="error">Error filtering logs: ' + error.message + '</div>';
                    }
                }
                
                async function exportLogs() {
                    try {
                        const response = await fetch('/admin/logs/export');
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `logs_export_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.json`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    } catch (error) {
                        alert('Export failed: ' + error.message);
                    }
                }
                
                function toggleCompactView() {
                    compactMode = !compactMode;
                    const btn = document.getElementById('compact-btn');
                    const container = document.querySelector('.logs-container');
                    
                    if (compactMode) {
                        btn.textContent = '📋 Full View';
                        container.style.fontSize = '0.8em';
                        container.classList.add('compact-mode');
                    } else {
                        btn.textContent = '📱 Compact View';
                        container.style.fontSize = '';
                        container.classList.remove('compact-mode');
                    }
                    
                    // Refresh to apply new formatting
                    refreshLogs();
                }
                
                async function clearLogs() {
                    if (confirm('Are you sure you want to clear the log buffer?')) {
                        try {
                            await fetch('/admin/logs/clear', { method: 'POST' });
                            refreshLogs();
                        } catch (error) {
                            alert('Error clearing logs: ' + error.message);
                        }
                    }
                }
                
                // Initial load - wait for DOM to be ready
                document.addEventListener('DOMContentLoaded', function() {
                    console.log('🚀 DOM loaded, starting dashboard...');
                    fetchDashboardData();
                });
                
                // Fallback if DOM is already loaded
                if (document.readyState === 'loading') {
                    // Do nothing, DOMContentLoaded will fire
                } else {
                    // DOM is already loaded
                    console.log('🚀 DOM already loaded, starting dashboard immediately...');
                    fetchDashboardData();
                }
                
                // Auto-refresh functionality
                setInterval(() => {
                    const autoRefreshCheckbox = document.getElementById('auto-refresh');
                    if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
                        fetchDashboardData();
                    }
                }, 10000);
                
                // Add event listeners for filters with debouncing
                let filterTimeout;
                function debounceFilter() {
                    clearTimeout(filterTimeout);
                    filterTimeout = setTimeout(refreshLogs, 300);
                }
                
                document.getElementById('level-filter').addEventListener('change', refreshLogs);
                document.getElementById('logger-filter').addEventListener('input', debounceFilter);
                document.getElementById('request-filter').addEventListener('input', debounceFilter);
                document.getElementById('message-filter').addEventListener('input', debounceFilter);
                document.getElementById('limit-filter').addEventListener('change', refreshLogs);
            </script>
        </body>
        </html>
        """
        return html_content
    
    @app.get("/admin/logs/api", response_model=LogDashboardResponse)
    async def get_dashboard_data():
        """Get dashboard data as JSON"""
        recent_logs = [asdict(entry) for entry in log_buffer.get_recent_entries(100)]
        stats = log_buffer.get_stats()
        logger_tree = get_logger_tree()
        system_info = get_system_info()
        
        return LogDashboardResponse(
            recent_logs=recent_logs,
            stats=stats,
            logger_tree=logger_tree,
            system_info=system_info
        )
    
    @app.post("/admin/logs/filter")
    async def filter_logs_endpoint(filters: LogFilterRequest):
        """Filter logs based on criteria"""
        all_entries = log_buffer.get_recent_entries(2000)  # Get more entries for filtering
        filtered_entries = filter_logs(all_entries, filters)
        
        return {
            "logs": [asdict(entry) for entry in filtered_entries],
            "total_filtered": len(filtered_entries),
            "total_available": len(all_entries)
        }
    
    @app.post("/admin/logs/clear")
    async def clear_logs_endpoint():
        """Clear the log buffer"""
        log_buffer.clear()
        logger.info("🗑️ Log buffer cleared via dashboard")
        return {"message": "Log buffer cleared successfully"}
    
    @app.get("/admin/logs/export")
    async def export_logs():
        """Export logs as JSON"""
        entries = log_buffer.get_recent_entries(2000)
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_entries": len(entries),
            "logs": [asdict(entry) for entry in entries]
        }
        
        return JSONResponse(
            content=export_data,
            headers={"Content-Disposition": "attachment; filename=logs_export.json"}
        )
    
    if PROMETHEUS_AVAILABLE:
        @app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint"""
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
    logger.info("🔧 Logging dashboard routes configured")


# Utility function for health checks
def get_logging_health() -> Dict[str, Any]:
    """Get logging system health status"""
    root_logger = logging.getLogger()
    handlers_info = []
    
    for handler in root_logger.handlers:
        handlers_info.append({
            "type": type(handler).__name__,
            "level": logging.getLevelName(handler.level),
            "formatter": type(handler.formatter).__name__ if handler.formatter else None
        })
    
    return {
        "status": "healthy",
        "root_logger_level": logging.getLevelName(root_logger.level),
        "handlers_count": len(root_logger.handlers),
        "handlers": handlers_info,
        "buffer_size": len(log_buffer.buffer),
        "buffer_stats": log_buffer.get_stats(),
        "opentelemetry_available": OPENTELEMETRY_AVAILABLE,
        "prometheus_available": PROMETHEUS_AVAILABLE,
    }