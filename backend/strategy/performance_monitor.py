"""
Performance Monitoring for Python Strategy Engine.

Provides comprehensive performance tracking including processing times,
memory usage, and system health metrics.
"""

from __future__ import annotations
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from contextlib import contextmanager

from backend.strategy.logging_config import get_component_logger, performance_logger


class PerformanceMonitor:
    """
    Monitors strategy engine performance metrics.
    
    Tracks processing times, memory usage, and system health to ensure
    the engine meets performance requirements (sub-5s processing, <512MB memory).
    """
    
    def __init__(self):
        from datetime import timezone
        self.logger = get_component_logger("performance_monitor")
        self.process = psutil.Process()
        self.start_time = datetime.now(timezone.utc)
        
        # Performance thresholds
        self.max_processing_time = 5.0  # seconds
        self.max_memory_mb = 512  # MB
        self.warning_memory_mb = 400  # MB (80% of limit)
        
        # Metrics storage
        self.cycle_count = 0
        self.total_processing_time = 0.0
        self.violations = {
            "processing_time": 0,
            "memory_usage": 0
        }
    
    @contextmanager
    def track_operation(self, operation_name: str):
        """
        Context manager to track operation performance.
        
        Usage:
            with monitor.track_operation("data_fetch"):
                # ... operation code ...
        """
        start_time = time.time()
        start_memory = self.get_memory_usage_mb()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            end_memory = self.get_memory_usage_mb()
            memory_delta = end_memory - start_memory
            
            # Log metrics
            performance_logger.log_processing_time(operation_name, duration)
            
            if memory_delta > 0:
                self.logger.debug(
                    f"{operation_name} memory delta: +{memory_delta:.2f}MB"
                )
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
            return memory_mb
        except Exception as e:
            self.logger.error(f"Error getting memory usage: {e}")
            return 0.0
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return self.process.cpu_percent(interval=0.1)
        except Exception as e:
            self.logger.error(f"Error getting CPU usage: {e}")
            return 0.0
    
    def check_memory_threshold(self) -> tuple[bool, Optional[str]]:
        """
        Check if memory usage is within acceptable limits.
        
        Returns:
            Tuple of (within_limits, warning_message)
        """
        memory_mb = self.get_memory_usage_mb()
        performance_logger.log_memory_usage("strategy_engine", memory_mb)
        
        if memory_mb > self.max_memory_mb:
            self.violations["memory_usage"] += 1
            return False, f"Memory limit exceeded: {memory_mb:.2f}MB > {self.max_memory_mb}MB"
        
        if memory_mb > self.warning_memory_mb:
            return True, f"Memory usage high: {memory_mb:.2f}MB (warning threshold: {self.warning_memory_mb}MB)"
        
        return True, None
    
    def check_processing_time(self, duration: float) -> tuple[bool, Optional[str]]:
        """
        Check if processing time is within acceptable limits.
        
        Returns:
            Tuple of (within_limits, warning_message)
        """
        if duration > self.max_processing_time:
            self.violations["processing_time"] += 1
            return False, f"Processing time exceeded: {duration:.3f}s > {self.max_processing_time}s"
        
        return True, None
    
    def record_cycle_completion(self, duration: float):
        """Record completion of a processing cycle."""
        self.cycle_count += 1
        self.total_processing_time += duration
        
        # Check thresholds
        time_ok, time_msg = self.check_processing_time(duration)
        memory_ok, memory_msg = self.check_memory_threshold()
        
        if not time_ok:
            self.logger.warning(time_msg)
        
        if not memory_ok:
            self.logger.error(memory_msg)
        elif memory_msg:
            self.logger.warning(memory_msg)
    
    def get_uptime_seconds(self) -> float:
        """Get engine uptime in seconds."""
        from datetime import timezone
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def get_average_cycle_time(self) -> float:
        """Get average processing cycle time."""
        if self.cycle_count == 0:
            return 0.0
        return self.total_processing_time / self.cycle_count
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        uptime = self.get_uptime_seconds()
        memory_mb = self.get_memory_usage_mb()
        cpu_percent = self.get_cpu_usage()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "uptime_formatted": str(timedelta(seconds=int(uptime))),
            "cycle_count": self.cycle_count,
            "average_cycle_time": self.get_average_cycle_time(),
            "total_processing_time": self.total_processing_time,
            "memory_usage_mb": memory_mb,
            "memory_limit_mb": self.max_memory_mb,
            "memory_usage_percent": (memory_mb / self.max_memory_mb) * 100,
            "cpu_usage_percent": cpu_percent,
            "violations": self.violations.copy(),
            "performance_logger_metrics": performance_logger.get_metrics()
        }
        
        return metrics
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status for monitoring.
        
        Returns:
            Health status with overall assessment.
        """
        metrics = self.get_performance_metrics()
        
        # Determine health status
        status = "healthy"
        issues = []
        
        # Check memory
        if metrics["memory_usage_mb"] > self.max_memory_mb:
            status = "unhealthy"
            issues.append(f"Memory limit exceeded: {metrics['memory_usage_mb']:.2f}MB")
        elif metrics["memory_usage_mb"] > self.warning_memory_mb:
            if status == "healthy":
                status = "degraded"
            issues.append(f"Memory usage high: {metrics['memory_usage_mb']:.2f}MB")
        
        # Check processing time
        if metrics["average_cycle_time"] > self.max_processing_time:
            status = "unhealthy"
            issues.append(f"Average cycle time exceeded: {metrics['average_cycle_time']:.3f}s")
        elif metrics["average_cycle_time"] > self.max_processing_time * 0.8:
            if status == "healthy":
                status = "degraded"
            issues.append(f"Average cycle time high: {metrics['average_cycle_time']:.3f}s")
        
        # Check violations
        if metrics["violations"]["processing_time"] > 0:
            issues.append(f"Processing time violations: {metrics['violations']['processing_time']}")
        
        if metrics["violations"]["memory_usage"] > 0:
            issues.append(f"Memory violations: {metrics['violations']['memory_usage']}")
        
        return {
            "status": status,
            "timestamp": metrics["timestamp"],
            "uptime": metrics["uptime_formatted"],
            "metrics": {
                "memory_mb": metrics["memory_usage_mb"],
                "memory_percent": metrics["memory_usage_percent"],
                "cpu_percent": metrics["cpu_usage_percent"],
                "avg_cycle_time": metrics["average_cycle_time"],
                "cycle_count": metrics["cycle_count"]
            },
            "issues": issues,
            "violations": metrics["violations"]
        }
    
    def reset_violations(self):
        """Reset violation counters."""
        self.violations = {
            "processing_time": 0,
            "memory_usage": 0
        }
        self.logger.info("Performance violation counters reset")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
