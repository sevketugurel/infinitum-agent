# File: src/infinitum/core/logging_config.py
"""
Advanced Cloud Logging configuration with enhanced traceability and monitoring
"""

import logging
import sys
import json
import uuid
import functools
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Union
from contextlib import contextmanager
from threading import local
import time
import asyncio
from contextvars import ContextVar

# Enhanced logging imports
try:
    import structlog
    from rich.logging import RichHandler
    from rich.console import Console
    from rich.traceback import install as install_rich_traceback
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    structlog = None

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.gcp.trace import CloudTraceSpanExporter
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from infinitum.settings import settings

# Thread-local storage for request context
_context_storage = local()

# Context variables for async request tracking
_request_id_var: ContextVar[str] = ContextVar('request_id', default='')
_user_id_var: ContextVar[str] = ContextVar('user_id', default='')
_session_id_var: ContextVar[str] = ContextVar('session_id', default='')

class EnhancedStructuredFormatter(logging.Formatter):
    """Enhanced formatter for structured JSON logging with correlation IDs and tracing"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get correlation IDs from context
        request_id = getattr(_context_storage, 'request_id', None) or _request_id_var.get('')
        user_id = getattr(_context_storage, 'user_id', None) or _user_id_var.get('')
        session_id = getattr(_context_storage, 'session_id', None) or _session_id_var.get('')
        
        # Create structured log entry with enhanced fields
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread_id": record.thread,
            "process_id": record.process,
        }
        
        # Add correlation IDs if available
        if request_id:
            log_entry['request_id'] = request_id
        if user_id:
            log_entry['user_id'] = user_id
        if session_id:
            log_entry['session_id'] = session_id
            
        # Add trace context from OpenTelemetry
        if OPENTELEMETRY_AVAILABLE:
            span = trace.get_current_span()
            if span and span.is_recording():
                span_context = span.get_span_context()
                log_entry['trace_id'] = format(span_context.trace_id, '032x')
                log_entry['span_id'] = format(span_context.span_id, '016x')
        
        # Add custom fields from extra
        for key, value in getattr(record, '__dict__', {}).items():
            if key.startswith('custom_') or key in [
                'user_query', 'step_number', 'step_name', 'success', 'error', 
                'processing_time', 'endpoint', 'http_method', 'status_code',
                'operation', 'component', 'business_context'
            ]:
                # Clean key name
                clean_key = key.replace('custom_', '')
                if key == 'processing_time':
                    log_entry['processing_time_seconds'] = value
                else:
                    log_entry[clean_key] = value
            
        # Add exception info with enhanced details
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_entry['exception'] = {
                'type': exc_type.__name__ if exc_type else None,
                'message': str(exc_value) if exc_value else None,
                'traceback': self.formatException(record.exc_info)
            }
            
        # Add stack trace for errors
        if record.levelno >= logging.ERROR and record.stack_info:
            log_entry['stack_trace'] = record.stack_info
            
        # Add performance metadata for slow operations
        if hasattr(record, 'processing_time') and record.processing_time > 1.0:
            log_entry['performance_warning'] = True
            log_entry['slow_operation'] = True
            
        return json.dumps(log_entry, default=str)  # default=str handles datetime serialization


class StructuredFormatter(EnhancedStructuredFormatter):
    """Backward compatibility alias"""
    pass

def setup_enhanced_logging():
    """Setup enhanced logging with multiple handlers and integrations"""
    
    # Initialize Sentry for error tracking
    if SENTRY_AVAILABLE and settings.SENTRY_DSN:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                sentry_logging,
                FastApiIntegration(auto_enabling_integrations=False),
            ],
            traces_sample_rate=0.1,  # Sample 10% of traces
            profiles_sample_rate=0.1,
            attach_stacktrace=True,
            send_default_pii=False,
            environment=settings.ENVIRONMENT
        )
    
    # Initialize OpenTelemetry tracing
    if OPENTELEMETRY_AVAILABLE and settings.ENVIRONMENT == "production":
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        # Configure Google Cloud Trace exporter
        if settings.GOOGLE_CLOUD_PROJECT:
            cloud_trace_exporter = CloudTraceSpanExporter(
                project_id=settings.GOOGLE_CLOUD_PROJECT
            )
            span_processor = BatchSpanProcessor(cloud_trace_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
        # Instrument logging
        LoggingInstrumentor().instrument(set_logging_format=True)
    
    # Setup Rich for development
    if RICH_AVAILABLE and settings.ENVIRONMENT == "development":
        install_rich_traceback(show_locals=True)
        console = Console()
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handlers based on environment
    if settings.ENVIRONMENT == "production":
        # Production: Structured JSON logging
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = EnhancedStructuredFormatter()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler for persistent logging
        if hasattr(settings, 'LOG_FILE_PATH') and settings.LOG_FILE_PATH:
            file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    else:
        # Development: Rich or simple formatting
        if RICH_AVAILABLE:
            # Use Rich handler for beautiful console output
            rich_handler = RichHandler(
                console=console,
                show_time=True,
                show_level=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True
            )
            root_logger.addHandler(rich_handler)
        else:
            # Fallback to enhanced simple formatter
            console_handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s | %(name)-20s | %(levelname)-8s | %(funcName)-15s:%(lineno)-4d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
    
    # Set log levels
    if settings.ENVIRONMENT == "development":
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)
    
    # Configure specific logger levels with more granular control
    logger_configs = {
        "uvicorn.access": logging.INFO,
        "uvicorn.error": logging.INFO,
        "uvicorn": logging.INFO,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "google.cloud": logging.WARNING,
        "google.auth": logging.WARNING,
        "urllib3.connectionpool": logging.WARNING,
        "asyncio": logging.WARNING,
        "crewai": logging.INFO,
        "agent": logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
    }
    
    for logger_name, level in logger_configs.items():
        logging.getLogger(logger_name).setLevel(level)
    
    return root_logger


def setup_cloud_logging():
    """Backward compatibility wrapper"""
    return setup_enhanced_logging()

def get_agent_logger(name: str) -> logging.Logger:
    """Get a logger instance configured for agent operations"""
    return logging.getLogger(f"agent.{name}")


# Context Management Functions
def set_request_context(request_id: str = None, user_id: str = None, session_id: str = None):
    """Set request context for correlation IDs"""
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    # Set in thread-local storage for sync contexts
    _context_storage.request_id = request_id
    if user_id:
        _context_storage.user_id = user_id
    if session_id:
        _context_storage.session_id = session_id
    
    # Set in context variables for async contexts
    _request_id_var.set(request_id)
    if user_id:
        _user_id_var.set(user_id)
    if session_id:
        _session_id_var.set(session_id)
    
    return request_id


def get_request_context() -> Dict[str, str]:
    """Get current request context"""
    return {
        'request_id': getattr(_context_storage, 'request_id', None) or _request_id_var.get(''),
        'user_id': getattr(_context_storage, 'user_id', None) or _user_id_var.get(''),
        'session_id': getattr(_context_storage, 'session_id', None) or _session_id_var.get(''),
    }


@contextmanager
def log_context(**context):
    """Context manager for adding context to logs"""
    original_values = {}
    
    # Store original values and set new ones
    for key, value in context.items():
        original_values[key] = getattr(_context_storage, key, None)
        setattr(_context_storage, key, value)
    
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                delattr(_context_storage, key)
            else:
                setattr(_context_storage, key, original_value)


# Enhanced Logging Decorators
def log_function_call(
    logger: logging.Logger = None,
    log_args: bool = False,
    log_result: bool = False,
    log_performance: bool = True,
    level: int = logging.INFO
):
    """Decorator to automatically log function calls with timing"""
    def decorator(func: Callable) -> Callable:
        if logger is None:
            func_logger = logging.getLogger(func.__module__)
        else:
            func_logger = logger
            
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            # Log function entry
            extra = {
                'operation': f"{func.__module__}.{func_name}",
                'component': func.__module__.split('.')[-1],
            }
            
            if log_args and args:
                extra['function_args'] = str(args)[:200]  # Truncate long args
            if log_args and kwargs:
                extra['function_kwargs'] = str(kwargs)[:200]
            
            func_logger.log(level, f"🚀 Starting {func_name}", extra=extra)
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                end_time = time.time()
                duration = end_time - start_time
                
                extra.update({
                    'success': True,
                    'processing_time': duration,
                })
                
                if log_result and result is not None:
                    extra['function_result'] = str(result)[:200]
                
                if log_performance and duration > 1.0:
                    func_logger.warning(f"⚠️  Slow function {func_name} completed in {duration:.2f}s", extra=extra)
                else:
                    func_logger.log(level, f"✅ Completed {func_name} in {duration:.2f}s", extra=extra)
                
                return result
                
            except Exception as e:
                # Log error
                end_time = time.time()
                duration = end_time - start_time
                
                extra.update({
                    'success': False,
                    'processing_time': duration,
                    'error': str(e),
                    'exception_type': type(e).__name__
                })
                
                func_logger.error(f"❌ Failed {func_name} after {duration:.2f}s: {e}", extra=extra, exc_info=True)
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            # Log function entry
            extra = {
                'operation': f"{func.__module__}.{func_name}",
                'component': func.__module__.split('.')[-1],
                'async_function': True,
            }
            
            if log_args and args:
                extra['function_args'] = str(args)[:200]
            if log_args and kwargs:
                extra['function_kwargs'] = str(kwargs)[:200]
            
            func_logger.log(level, f"🚀 Starting async {func_name}", extra=extra)
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful completion
                end_time = time.time()
                duration = end_time - start_time
                
                extra.update({
                    'success': True,
                    'processing_time': duration,
                })
                
                if log_result and result is not None:
                    extra['function_result'] = str(result)[:200]
                
                if log_performance and duration > 1.0:
                    func_logger.warning(f"⚠️  Slow async function {func_name} completed in {duration:.2f}s", extra=extra)
                else:
                    func_logger.log(level, f"✅ Completed async {func_name} in {duration:.2f}s", extra=extra)
                
                return result
                
            except Exception as e:
                # Log error
                end_time = time.time()
                duration = end_time - start_time
                
                extra.update({
                    'success': False,
                    'processing_time': duration,
                    'error': str(e),
                    'exception_type': type(e).__name__
                })
                
                func_logger.error(f"❌ Failed async {func_name} after {duration:.2f}s: {e}", extra=extra, exc_info=True)
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_business_event(
    logger: logging.Logger,
    event_name: str,
    business_context: str = None,
    **event_data
):
    """Log a business event with structured data"""
    extra = {
        'event_type': 'business_event',
        'event_name': event_name,
        'business_context': business_context or 'general',
    }
    extra.update(event_data)
    
    logger.info(f"📊 Business Event: {event_name}", extra=extra)

def log_agent_step(
    logger: logging.Logger,
    step_number: int,
    step_name: str,
    session_id: str,
    user_query: str,
    success: bool = True,
    error: str = None,
    processing_time: float = None,
    **extra_fields
):
    """
    Structured logging function for agent steps with all relevant context.
    
    Args:
        logger: Logger instance
        step_number: Step number (1-5)
        step_name: Name of the step
        session_id: Session identifier
        user_query: Original user query
        success: Whether the step succeeded
        error: Error message if failed
        processing_time: Time taken for this step
        **extra_fields: Additional fields to log
    """
    
    level = logging.INFO if success else logging.ERROR
    message = f"Agent Step {step_number} - {step_name} - {'SUCCESS' if success else 'FAILED'}"
    
    # Create log record with extra fields
    extra = {
        'session_id': session_id,
        'user_query': user_query[:100],  # Truncate long queries
        'step_number': step_number,
        'step_name': step_name,
        'success': success,
        'processing_time': processing_time
    }
    
    if error:
        extra['error'] = error
        
    # Add any additional fields
    extra.update(extra_fields)
    
    logger.log(level, message, extra=extra)

def log_api_request(
    logger: logging.Logger,
    endpoint: str,
    method: str,
    user_query: str = None,
    session_id: str = None,
    status_code: int = None,
    processing_time: float = None,
    error: str = None
):
    """
    Structured logging for API requests.
    
    Args:
        logger: Logger instance
        endpoint: API endpoint path
        method: HTTP method
        user_query: User query if applicable
        session_id: Session ID if available
        status_code: HTTP status code
        processing_time: Request processing time
        error: Error message if failed
    """
    
    level = logging.INFO if not error else logging.ERROR
    message = f"API {method} {endpoint} - {status_code or 'PROCESSING'}"
    
    extra = {
        'endpoint': endpoint,
        'http_method': method,
        'status_code': status_code,
        'processing_time': processing_time
    }
    
    if user_query:
        extra['user_query'] = user_query[:100]
    if session_id:
        extra['session_id'] = session_id
    if error:
        extra['error'] = error
        
    logger.log(level, message, extra=extra)

# Performance monitoring helpers
class PerformanceTimer:
    """Context manager for timing operations and logging performance"""
    
    def __init__(self, logger: logging.Logger, operation_name: str, **extra_context):
        self.logger = logger
        self.operation_name = operation_name
        self.extra_context = extra_context
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation_name}", extra=self.extra_context)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        extra = self.extra_context.copy()
        extra['processing_time'] = duration
        extra['operation'] = self.operation_name
        
        if exc_type is None:
            self.logger.info(f"Completed {self.operation_name} in {duration:.2f}s", extra=extra)
        else:
            extra['error'] = str(exc_val)
            self.logger.error(f"Failed {self.operation_name} after {duration:.2f}s", extra=extra)

# Metrics and Monitoring Integration
try:
    from prometheus_client import Counter, Histogram, Gauge
    
    # Define metrics
    LOG_ENTRIES_TOTAL = Counter('log_entries_total', 'Total log entries', ['level', 'logger_name'])
    LOG_PROCESSING_TIME = Histogram('log_processing_seconds', 'Time spent processing logs')
    ACTIVE_REQUESTS = Gauge('active_requests_total', 'Number of active requests')
    
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MetricsHandler(logging.Handler):
    """Logging handler that exports metrics to Prometheus"""
    
    def emit(self, record):
        if PROMETHEUS_AVAILABLE:
            LOG_ENTRIES_TOTAL.labels(
                level=record.levelname.lower(),
                logger_name=record.name.split('.')[0]
            ).inc()


class EnhancedPerformanceTimer:
    """Enhanced performance timer with OpenTelemetry tracing support"""
    
    def __init__(self, 
                 logger: logging.Logger, 
                 operation_name: str, 
                 trace_operation: bool = True,
                 **extra_context):
        self.logger = logger
        self.operation_name = operation_name
        self.extra_context = extra_context
        self.trace_operation = trace_operation
        self.start_time = None
        self.span = None
        
    def __enter__(self):
        self.start_time = time.time()
        
        # Start OpenTelemetry span if available
        if OPENTELEMETRY_AVAILABLE and self.trace_operation:
            tracer = trace.get_tracer(__name__)
            self.span = tracer.start_span(self.operation_name)
            self.span.set_attribute("operation.name", self.operation_name)
            for key, value in self.extra_context.items():
                self.span.set_attribute(f"operation.{key}", str(value))
        
        extra = self.extra_context.copy()
        extra['operation'] = self.operation_name
        self.logger.info(f"⏱️  Starting {self.operation_name}", extra=extra)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration = end_time - self.start_time
        
        extra = self.extra_context.copy()
        extra['processing_time'] = duration
        extra['operation'] = self.operation_name
        
        # Update span with results
        if self.span:
            self.span.set_attribute("duration_seconds", duration)
            if exc_type is None:
                self.span.set_attribute("success", True)
            else:
                self.span.set_attribute("success", False)
                self.span.set_attribute("error.type", exc_type.__name__)
                self.span.set_attribute("error.message", str(exc_val))
            self.span.end()
        
        if exc_type is None:
            if duration > 1.0:
                self.logger.warning(f"⚠️  Slow operation {self.operation_name} completed in {duration:.2f}s", extra=extra)
            else:
                self.logger.info(f"✅ Completed {self.operation_name} in {duration:.2f}s", extra=extra)
        else:
            extra['error'] = str(exc_val)
            extra['exception_type'] = exc_type.__name__
            self.logger.error(f"❌ Failed {self.operation_name} after {duration:.2f}s", extra=extra, exc_info=True)


# Log Sampling and Filtering
class SamplingFilter(logging.Filter):
    """Filter to sample logs for performance optimization"""
    
    def __init__(self, sample_rate: float = 1.0, high_priority_levels=None):
        super().__init__()
        self.sample_rate = sample_rate
        self.high_priority_levels = high_priority_levels or {logging.ERROR, logging.CRITICAL}
        self.counter = 0
        
    def filter(self, record):
        # Always allow high priority logs
        if record.levelno in self.high_priority_levels:
            return True
            
        # Sample other logs
        self.counter += 1
        return (self.counter % int(1 / self.sample_rate)) == 0


class NoiseFilter(logging.Filter):
    """Filter to reduce noise from verbose libraries"""
    
    def __init__(self):
        super().__init__()
        self.noise_patterns = [
            'favicon.ico',
            'healthz',
            'metrics',
            'Connection broken',
            'Retrying',
        ]
        
    def filter(self, record):
        message = record.getMessage()
        return not any(pattern in message for pattern in self.noise_patterns)


# Debug and Development Helpers
def get_logger_tree():
    """Get a tree view of all active loggers for debugging"""
    loggers = []
    for name in sorted(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        loggers.append({
            'name': name,
            'level': logger.level,
            'effective_level': logger.getEffectiveLevel(),
            'handlers': len(logger.handlers),
            'propagate': logger.propagate
        })
    return loggers


def setup_debug_logging():
    """Setup additional debug logging for development"""
    debug_logger = logging.getLogger('debug')
    debug_logger.setLevel(logging.DEBUG)
    
    # Add debug file handler
    debug_handler = logging.FileHandler('logs/debug.log')
    debug_formatter = logging.Formatter(
        '%(asctime)s | %(name)-30s | %(levelname)-8s | %(funcName)-20s:%(lineno)-4d | %(message)s'
    )
    debug_handler.setFormatter(debug_formatter)
    debug_logger.addHandler(debug_handler)
    
    return debug_logger


def log_system_info(logger: logging.Logger):
    """Log system information for debugging"""
    import platform
    import psutil
    import os
    
    system_info = {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(),
        'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
        'disk_usage_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
        'environment': settings.ENVIRONMENT,
        'process_id': os.getpid(),
    }
    
    logger.info("🔧 System Information", extra=system_info)


# Structured Logging Helpers
def create_logger_with_context(name: str, **default_context) -> logging.Logger:
    """Create a logger with default context"""
    logger = logging.getLogger(name)
    
    # Add a custom method to log with default context
    def log_with_context(level, message, **extra_context):
        combined_context = default_context.copy()
        combined_context.update(extra_context)
        logger.log(level, message, extra=combined_context)
    
    logger.log_with_context = log_with_context
    return logger


# Backward compatibility aliases
PerformanceTimer = EnhancedPerformanceTimer

# Initialize logging when module is imported
setup_enhanced_logging()

# Add metrics handler if Prometheus is available
if PROMETHEUS_AVAILABLE:
    metrics_handler = MetricsHandler()
    logging.getLogger().addHandler(metrics_handler)