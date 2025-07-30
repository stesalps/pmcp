#!/usr/bin/env python3
"""
Google Manus System - Improvements and Utilities

This module contains improvements and utility functions for the Google Manus System,
including enhanced error handling, configuration management, and system utilities.
"""

import os
import sys
import json
import logging
import asyncio
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
import time

# Enhanced Error Handling
class ManusError(Exception):
    """Base exception for Manus system errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "MANUS_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

class ModelError(ManusError):
    """Error related to AI model operations"""
    def __init__(self, message: str, model_type: str = None, **kwargs):
        super().__init__(message, "MODEL_ERROR", {"model_type": model_type, **kwargs})

class ToolError(ManusError):
    """Error related to tool execution"""
    def __init__(self, message: str, tool_name: str = None, **kwargs):
        super().__init__(message, "TOOL_ERROR", {"tool_name": tool_name, **kwargs})

class DeploymentError(ManusError):
    """Error related to web deployment"""
    def __init__(self, message: str, site_name: str = None, **kwargs):
        super().__init__(message, "DEPLOYMENT_ERROR", {"site_name": site_name, **kwargs})

# Enhanced Configuration Management
class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config_name = config_file.stem
                    self._configs[config_name] = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load config {config_file}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support"""
        keys = key.split('.')
        value = self._configs
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, config_name: str = "user_config"):
        """Set configuration value"""
        if config_name not in self._configs:
            self._configs[config_name] = {}
        
        keys = key.split('.')
        config = self._configs[config_name]
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save_config(config_name)
    
    def _save_config(self, config_name: str):
        """Save configuration to file"""
        config_file = self.config_dir / f"{config_name}.json"
        with open(config_file, 'w') as f:
            json.dump(self._configs[config_name], f, indent=2)

# Enhanced Logging System
class ManusLogger:
    """Enhanced logging system for Manus"""
    
    def __init__(self, log_dir: Path, log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = getattr(logging, log_level.upper())
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler for all logs
        all_logs_handler = logging.FileHandler(self.log_dir / "manus_all.log")
        all_logs_handler.setLevel(logging.DEBUG)
        all_logs_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(all_logs_handler)
        
        # Error-only file handler
        error_handler = logging.FileHandler(self.log_dir / "manus_errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Tool execution handler
        tool_handler = logging.FileHandler(self.log_dir / "manus_tools.log")
        tool_handler.setLevel(logging.INFO)
        tool_handler.setFormatter(detailed_formatter)
        
        # Create tool logger
        tool_logger = logging.getLogger("manus.tools")
        tool_logger.addHandler(tool_handler)
        tool_logger.setLevel(logging.INFO)

# Performance Monitoring
class PerformanceMonitor:
    """Monitor system performance and usage"""
    
    def __init__(self):
        self.metrics = {
            "tool_executions": {},
            "model_requests": {},
            "api_calls": {},
            "errors": {},
            "response_times": {}
        }
        self.start_time = datetime.now()
    
    def record_tool_execution(self, tool_name: str, execution_time: float, success: bool):
        """Record tool execution metrics"""
        if tool_name not in self.metrics["tool_executions"]:
            self.metrics["tool_executions"][tool_name] = {
                "count": 0,
                "total_time": 0,
                "successes": 0,
                "failures": 0
            }
        
        stats = self.metrics["tool_executions"][tool_name]
        stats["count"] += 1
        stats["total_time"] += execution_time
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
    
    def record_model_request(self, model_type: str, model_name: str, response_time: float):
        """Record model request metrics"""
        key = f"{model_type}:{model_name}"
        if key not in self.metrics["model_requests"]:
            self.metrics["model_requests"][key] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0
            }
        
        stats = self.metrics["model_requests"][key]
        stats["count"] += 1
        stats["total_time"] += response_time
        stats["avg_time"] = stats["total_time"] / stats["count"]
    
    def record_error(self, error_type: str, error_message: str):
        """Record error occurrence"""
        if error_type not in self.metrics["errors"]:
            self.metrics["errors"][error_type] = {
                "count": 0,
                "messages": []
            }
        
        self.metrics["errors"][error_type]["count"] += 1
        self.metrics["errors"][error_type]["messages"].append({
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        uptime = datetime.now() - self.start_time
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime),
            "total_tool_executions": sum(
                stats["count"] for stats in self.metrics["tool_executions"].values()
            ),
            "total_model_requests": sum(
                stats["count"] for stats in self.metrics["model_requests"].values()
            ),
            "total_errors": sum(
                stats["count"] for stats in self.metrics["errors"].values()
            ),
            "most_used_tool": max(
                self.metrics["tool_executions"].items(),
                key=lambda x: x[1]["count"],
                default=("none", {"count": 0})
            )[0],
            "metrics": self.metrics
        }

# Retry Decorator
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,)):
    """Retry decorator with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise e
                    
                    logging.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay} seconds..."
                    )
                    
                    await asyncio.sleep(current_delay)
                    attempt += 1
                    current_delay *= backoff
            
            return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise e
                    
                    logging.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay} seconds..."
                    )
                    
                    time.sleep(current_delay)
                    attempt += 1
                    current_delay *= backoff
            
            return None
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Input Validation
class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_file_path(path: str, must_exist: bool = False) -> bool:
        """Validate file path"""
        try:
            path_obj = Path(path)
            
            # Check for path traversal attacks
            if ".." in str(path_obj) or str(path_obj).startswith("/"):
                return False
            
            if must_exist and not path_obj.exists():
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_code(code: str, max_length: int = 10000) -> bool:
        """Validate code input"""
        if not isinstance(code, str):
            return False
        
        if len(code) > max_length:
            return False
        
        # Check for potentially dangerous imports/operations
        dangerous_patterns = [
            "import os",
            "import subprocess",
            "import sys",
            "__import__",
            "eval(",
            "exec(",
            "open(",
            "file("
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                logging.warning(f"Potentially dangerous code pattern detected: {pattern}")
                # Don't reject, just warn - let the sandboxed execution handle it
        
        return True
    
    @staticmethod
    def validate_json(json_str: str) -> tuple[bool, Optional[Dict]]:
        """Validate JSON string"""
        try:
            data = json.loads(json_str)
            return True, data
        except json.JSONDecodeError as e:
            return False, None

# System Health Checker
class HealthChecker:
    """System health monitoring"""
    
    def __init__(self, config_manager: ConfigManager, performance_monitor: PerformanceMonitor):
        self.config_manager = config_manager
        self.performance_monitor = performance_monitor
        self.last_check = datetime.now()
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "metrics": {},
            "warnings": [],
            "errors": []
        }
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            disk_usage_percent = (used / total) * 100
            
            health_status["components"]["disk"] = {
                "status": "healthy" if disk_usage_percent < 90 else "warning",
                "usage_percent": disk_usage_percent,
                "free_gb": free // (1024**3)
            }
            
            if disk_usage_percent > 90:
                health_status["warnings"].append("Disk usage is above 90%")
        except Exception as e:
            health_status["components"]["disk"] = {"status": "error", "error": str(e)}
            health_status["errors"].append(f"Disk check failed: {e}")
        
        # Check memory usage
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            health_status["components"]["memory"] = {
                "status": "healthy" if memory.percent < 90 else "warning",
                "usage_percent": memory.percent,
                "available_gb": memory.available // (1024**3)
            }
            
            if memory.percent > 90:
                health_status["warnings"].append("Memory usage is above 90%")
        except ImportError:
            health_status["components"]["memory"] = {
                "status": "unknown", 
                "error": "psutil not available"
            }
        except Exception as e:
            health_status["components"]["memory"] = {"status": "error", "error": str(e)}
            health_status["errors"].append(f"Memory check failed: {e}")
        
        # Check model availability
        try:
            # This would need to be imported from the main system
            # health_status["components"]["models"] = await self._check_models()
            pass
        except Exception as e:
            health_status["errors"].append(f"Model check failed: {e}")
        
        # Add performance metrics
        health_status["metrics"] = self.performance_monitor.get_summary()
        
        # Determine overall status
        if health_status["errors"]:
            health_status["overall_status"] = "unhealthy"
        elif health_status["warnings"]:
            health_status["overall_status"] = "warning"
        
        self.last_check = datetime.now()
        return health_status

# Utility Functions
class SystemUtils:
    """System utility functions"""
    
    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration to human readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations"""
        import re
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        # Limit length
        if len(filename) > 255:
            filename = filename[:255]
        return filename
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information"""
        import platform
        
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            import psutil
            info.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total // (1024**3),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            })
        except ImportError:
            pass
        
        return info

# Export main classes and functions
__all__ = [
    'ManusError', 'ModelError', 'ToolError', 'DeploymentError',
    'ConfigManager', 'ManusLogger', 'PerformanceMonitor',
    'retry', 'InputValidator', 'HealthChecker', 'SystemUtils'
]

if __name__ == "__main__":
    # Example usage
    print("Google Manus System - Improvements Module")
    print("This module provides enhanced error handling, configuration management,")
    print("and system utilities for the Google Manus System.")
    
    # Demo system info
    utils = SystemUtils()
    print("\nSystem Information:")
    for key, value in utils.get_system_info().items():
        print(f"  {key}: {value}")