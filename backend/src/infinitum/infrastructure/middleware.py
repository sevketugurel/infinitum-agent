# File: src/infinitum/core/middleware.py
"""
FastAPI middleware for enhanced request/response logging and tracing
"""

import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from infinitum.infrastructure.logging_config import (
    set_request_context, 
    get_agent_logger, 
    log_api_request,
    EnhancedPerformanceTimer,
    OPENTELEMETRY_AVAILABLE,
    PROMETHEUS_AVAILABLE
)

if OPENTELEMETRY_AVAILABLE:
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

if PROMETHEUS_AVAILABLE:
    from prometheus_client import Counter, Histogram, Gauge
    
    # Define request metrics
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
    ACTIVE_REQUESTS = Gauge('http_requests_active', 'Number of active HTTP requests')

logger = get_agent_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for request/response logging with correlation IDs"""
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ['/healthz', '/metrics', '/favicon.ico']
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate correlation ID and set context
        request_id = str(uuid.uuid4())
        user_id = request.headers.get('X-User-ID', '')
        session_id = request.headers.get('X-Session-ID', '')
        
        set_request_context(request_id=request_id, user_id=user_id, session_id=session_id)
        
        # Add correlation ID to request for downstream access
        request.state.request_id = request_id
        request.state.user_id = user_id
        request.state.session_id = session_id
        
        start_time = time.time()
        
        # Increment active request counter
        if PROMETHEUS_AVAILABLE:
            ACTIVE_REQUESTS.inc()
        
        # Log request details
        request_data = {
            'request_id': request_id,
            'method': request.method,
            'url': str(request.url),
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'headers': dict(request.headers),
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent', ''),
        }
        
        # Add request body if enabled (be careful with sensitive data)
        if self.log_request_body and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    request_data['body_size'] = len(body)
                    # Only log body for safe endpoints
                    if not any(sensitive in request.url.path.lower() for sensitive in ['auth', 'password', 'token']):
                        request_data['body_preview'] = body.decode('utf-8')[:500]
            except Exception as e:
                request_data['body_read_error'] = str(e)
        
        logger.info(f"🌐 Incoming {request.method} {request.url.path}", extra=request_data)
        
        # Create span for OpenTelemetry tracing
        span = None
        if OPENTELEMETRY_AVAILABLE:
            tracer = trace.get_tracer(__name__)
            span = tracer.start_span(f"{request.method} {request.url.path}")
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.user_agent", request.headers.get('user-agent', ''))
            span.set_attribute("request.id", request_id)
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response details
            response_data = {
                'request_id': request_id,
                'status_code': response.status_code,
                'processing_time': process_time,
                'response_headers': dict(response.headers),
            }
            
            # Add response body if enabled and safe
            if self.log_response_body and response.status_code >= 400:
                try:
                    # Only log error responses for debugging
                    if hasattr(response, 'body'):
                        body_size = len(response.body) if response.body else 0
                        response_data['response_body_size'] = body_size
                except Exception as e:
                    response_data['response_body_read_error'] = str(e)
            
            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = logging.ERROR
                status_category = "server_error"
            elif response.status_code >= 400:
                log_level = logging.WARNING
                status_category = "client_error"
            elif process_time > 2.0:
                log_level = logging.WARNING
                status_category = "slow_request"
            else:
                log_level = logging.INFO
                status_category = "success"
            
            response_data['status_category'] = status_category
            
            # Add correlation ID to response headers
            response.headers["X-Request-ID"] = request_id
            if user_id:
                response.headers["X-User-ID"] = user_id
            if session_id:
                response.headers["X-Session-ID"] = session_id
            
            # Log the response
            message = f"📤 Response {response.status_code} for {request.method} {request.url.path} in {process_time:.3f}s"
            logger.log(log_level, message, extra=response_data)
            
            # Update span with response data
            if span:
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("response.duration_ms", process_time * 1000)
                span.set_attribute("response.status_category", status_category)
                if response.status_code >= 400:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                span.end()
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code
                ).inc()
                REQUEST_DURATION.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).observe(process_time)
                ACTIVE_REQUESTS.dec()
            
            return response
            
        except Exception as e:
            # Handle exceptions
            process_time = time.time() - start_time
            
            error_data = {
                'request_id': request_id,
                'error': str(e),
                'exception_type': type(e).__name__,
                'processing_time': process_time,
            }
            
            logger.error(f"💥 Request failed for {request.method} {request.url.path}: {e}", 
                        extra=error_data, exc_info=True)
            
            # Update span with error
            if span:
                span.set_attribute("error.message", str(e))
                span.set_attribute("error.type", type(e).__name__)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                span.end()
            
            # Update metrics
            if PROMETHEUS_AVAILABLE:
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=500
                ).inc()
                ACTIVE_REQUESTS.dec()
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": "An unexpected error occurred"
                },
                headers={"X-Request-ID": request_id}
            )


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring application performance"""
    
    def __init__(self, app: ASGIApp, slow_request_threshold: float = 2.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log slow requests
            if process_time > self.slow_request_threshold:
                performance_data = {
                    'request_id': getattr(request.state, 'request_id', 'unknown'),
                    'method': request.method,
                    'path': request.url.path,
                    'processing_time': process_time,
                    'threshold_exceeded': True,
                    'performance_category': 'slow_request'
                }
                
                logger.warning(
                    f"🐌 Slow request detected: {request.method} {request.url.path} took {process_time:.2f}s",
                    extra=performance_data
                )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"💥 Performance monitoring caught exception after {process_time:.2f}s: {e}",
                extra={
                    'request_id': getattr(request.state, 'request_id', 'unknown'),
                    'processing_time': process_time,
                    'exception_type': type(e).__name__
                },
                exc_info=True
            )
            raise


def setup_logging_middleware(app: FastAPI):
    """Setup all logging-related middleware for the FastAPI app"""
    
    # Add OpenTelemetry instrumentation
    if OPENTELEMETRY_AVAILABLE:
        FastAPIInstrumentor.instrument_app(app)
    
    # Add performance monitoring middleware
    app.add_middleware(
        PerformanceMonitoringMiddleware,
        slow_request_threshold=2.0
    )
    
    # Add request logging middleware
    app.add_middleware(
        RequestLoggingMiddleware,
        log_request_body=False,  # Set to True for debugging, but be careful with sensitive data
        log_response_body=False,  # Only logs error responses
        exclude_paths=['/healthz', '/metrics', '/favicon.ico', '/docs', '/openapi.json']
    )
    
    logger.info("🔧 Logging middleware configured successfully")


# Utility functions for extracting context from requests
def get_request_id(request: Request) -> str:
    """Extract request ID from request state"""
    return getattr(request.state, 'request_id', '')


def get_user_id(request: Request) -> str:
    """Extract user ID from request state"""
    return getattr(request.state, 'user_id', '')


def get_session_id(request: Request) -> str:
    """Extract session ID from request state"""
    return getattr(request.state, 'session_id', '')


def log_request_context(request: Request, logger: logging.Logger, message: str, **extra):
    """Log a message with full request context"""
    context = {
        'request_id': get_request_id(request),
        'user_id': get_user_id(request),
        'session_id': get_session_id(request),
        'method': request.method,
        'path': request.url.path,
    }
    context.update(extra)
    logger.info(message, extra=context)