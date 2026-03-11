"""
Logging configuration for the Python Strategy Engine.

Provides structured logging with proper formatting and error handling
for all strategy engine components.
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any


class StrategyEngineFormatter(logging.Formatter):
    """Custom formatter for strategy engine logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with strategy engine context."""
        # Add timestamp
        record.timestamp = datetime.now().isoformat()
        
        # Add component context if available
        component = getattr(record, 'component', 'strategy')
        record.component = component
        
        # Format the message
        formatted = super().format(record)
        return formatted


def setup_strategy_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging for the strategy engine.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("strategy_engine")
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Create formatter
    formatter = StrategyEngineFormatter(
        fmt="%(timestamp)s | %(levelname)s | %(component)s | %(message)s"
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_component_logger(component_name: str) -> logging.Logger:
    """
    Get a logger for a specific strategy engine component.
    
    Args:
        component_name: Name of the component (e.g., 'market_data', 'bias_engine')
    
    Returns:
        Logger with component context
    """
    logger = logging.getLogger(f"strategy_engine.{component_name}")
    
    # Add component context to all log records
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.component = component_name
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    return logger


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self):
        self.logger = get_component_logger("performance")
        self.metrics: Dict[str, Any] = {}
        self.processing_times: Dict[str, list] = {}
        self.memory_samples: Dict[str, list] = {}
        self.error_counts: Dict[str, int] = {}
        self.max_samples = 100  # Keep last 100 samples for averaging
    
    def log_processing_time(self, operation: str, duration: float):
        """Log processing time for an operation."""
        self.logger.info(f"{operation} completed in {duration:.3f}s")
        
        # Store current duration
        self.metrics[f"{operation}_duration"] = duration
        
        # Track historical durations for averaging
        if operation not in self.processing_times:
            self.processing_times[operation] = []
        
        self.processing_times[operation].append(duration)
        
        # Keep only recent samples
        if len(self.processing_times[operation]) > self.max_samples:
            self.processing_times[operation] = self.processing_times[operation][-self.max_samples:]
        
        # Calculate and store average
        avg_duration = sum(self.processing_times[operation]) / len(self.processing_times[operation])
        self.metrics[f"{operation}_avg_duration"] = avg_duration
        
        # Track max duration
        max_duration = max(self.processing_times[operation])
        self.metrics[f"{operation}_max_duration"] = max_duration
        
        # Warn if exceeding thresholds
        if operation == "process_cycle" and duration > 5.0:
            self.logger.warning(f"Processing cycle exceeded 5s limit: {duration:.3f}s")
    
    def log_memory_usage(self, component: str, memory_mb: float):
        """Log memory usage for a component."""
        self.logger.debug(f"{component} memory usage: {memory_mb:.2f}MB")
        
        # Store current memory usage
        self.metrics[f"{component}_memory"] = memory_mb
        
        # Track historical memory usage
        if component not in self.memory_samples:
            self.memory_samples[component] = []
        
        self.memory_samples[component].append(memory_mb)
        
        # Keep only recent samples
        if len(self.memory_samples[component]) > self.max_samples:
            self.memory_samples[component] = self.memory_samples[component][-self.max_samples:]
        
        # Calculate and store average
        avg_memory = sum(self.memory_samples[component]) / len(self.memory_samples[component])
        self.metrics[f"{component}_avg_memory"] = avg_memory
        
        # Track peak memory
        peak_memory = max(self.memory_samples[component])
        self.metrics[f"{component}_peak_memory"] = peak_memory
        
        # Warn if approaching 512MB limit
        if memory_mb > 400:
            self.logger.warning(f"{component} memory usage high: {memory_mb:.2f}MB (limit: 512MB)")
    
    def log_data_metrics(self, operation: str, count: int, size_mb: float = None):
        """Log data operation metrics."""
        msg = f"{operation}: {count} items"
        if size_mb:
            msg += f", {size_mb:.2f}MB"
        self.logger.debug(msg)
        
        self.metrics[f"{operation}_count"] = count
        if size_mb:
            self.metrics[f"{operation}_size"] = size_mb
    
    def log_error(self, component: str, error_type: str):
        """Log error occurrence for tracking."""
        error_key = f"{component}_{error_type}"
        
        if error_key not in self.error_counts:
            self.error_counts[error_key] = 0
        
        self.error_counts[error_key] += 1
        self.metrics[f"error_{error_key}"] = self.error_counts[error_key]
        
        self.logger.error(f"{component} error: {error_type} (count: {self.error_counts[error_key]})")
    
    def log_signal_generated(self, grade: str, score: float):
        """Log signal generation metrics."""
        signal_key = f"signals_{grade.lower()}"
        
        if signal_key not in self.metrics:
            self.metrics[signal_key] = 0
        
        self.metrics[signal_key] += 1
        self.metrics["last_signal_score"] = score
        self.metrics["last_signal_grade"] = grade
        
        self.logger.info(f"Signal generated: {grade} (score: {score})")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = self.metrics.copy()
        
        # Add summary statistics
        if self.processing_times:
            metrics["processing_operations"] = list(self.processing_times.keys())
        
        if self.memory_samples:
            metrics["monitored_components"] = list(self.memory_samples.keys())
        
        if self.error_counts:
            metrics["total_errors"] = sum(self.error_counts.values())
            metrics["error_breakdown"] = self.error_counts.copy()
        
        return metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "processing_times": {},
            "memory_usage": {},
            "error_counts": self.error_counts.copy(),
            "signal_counts": {}
        }
        
        # Processing time summary
        for operation, durations in self.processing_times.items():
            if durations:
                summary["processing_times"][operation] = {
                    "current": durations[-1],
                    "average": sum(durations) / len(durations),
                    "max": max(durations),
                    "min": min(durations),
                    "samples": len(durations)
                }
        
        # Memory usage summary
        for component, samples in self.memory_samples.items():
            if samples:
                summary["memory_usage"][component] = {
                    "current": samples[-1],
                    "average": sum(samples) / len(samples),
                    "peak": max(samples),
                    "samples": len(samples)
                }
        
        # Signal counts
        for key, value in self.metrics.items():
            if key.startswith("signals_"):
                summary["signal_counts"][key] = value
        
        return summary
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics.clear()
        self.processing_times.clear()
        self.memory_samples.clear()
        # Don't reset error counts - keep for historical tracking


# Global instances
strategy_logger = setup_strategy_logging()
performance_logger = PerformanceLogger()