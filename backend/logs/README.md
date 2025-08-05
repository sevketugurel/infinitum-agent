# Logs

This directory contains application log files.

## Log Files

- `application.log` - Main application logs
- `debug.log` - Debug-level logs (development only)
- `error.log` - Error-specific logs
- `access.log` - HTTP access logs

## Configuration

Logging is configured in [`../src/infinitum/infrastructure/logging_config.py`](../src/infinitum/infrastructure/logging_config.py) and controlled by environment variables in [`../config/.env`](../config/.env):

### Environment Variables
- `LOG_LEVEL` - Minimum log level (DEBUG/INFO/WARNING/ERROR)
- `LOG_FILE_PATH` - Path to main log file
- `ENABLE_STRUCTURED_LOGGING` - Enable JSON structured logging
- `ENABLE_RICH_LOGGING` - Enable rich console output
- `LOG_SAMPLING_RATE` - Sample rate for high-volume logs

## Log Levels

- **DEBUG** - Detailed diagnostic information
- **INFO** - General operational messages
- **WARNING** - Warning messages for potential issues
- **ERROR** - Error messages for failures
- **CRITICAL** - Critical errors that may cause shutdown

## Log Format

### Structured Logging (JSON)
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "infinitum.api",
  "message": "Request processed",
  "request_id": "req-123",
  "user_id": "user-456",
  "duration_ms": 150
}
```

### Standard Logging
```
2024-01-01 12:00:00 [INFO] infinitum.api: Request processed (req-123)
```

## Log Rotation

Logs are automatically rotated to prevent disk space issues:
- **Size-based**: Rotate when file exceeds 10MB
- **Time-based**: Daily rotation
- **Retention**: Keep 30 days of logs

## Monitoring

### Log Dashboard
Access the logging dashboard at `/admin/logs/dashboard` (requires authentication).

### Log Analysis
```bash
# View recent errors
tail -f logs/error.log

# Search for specific patterns
grep "ERROR" logs/application.log

# View structured logs
jq '.' logs/application.log  # if using JSON format
```

## Security

- **Log files are excluded from git** (see `.gitignore`)
- **Sensitive data is filtered** from logs
- **Access logs may contain IP addresses** - handle according to privacy policy

## Troubleshooting

### No Logs Generated
1. Check file permissions on logs directory
2. Verify `LOG_FILE_PATH` environment variable
3. Ensure logging is enabled in configuration

### Log Files Too Large
1. Check log rotation configuration
2. Reduce `LOG_LEVEL` in production
3. Adjust `LOG_SAMPLING_RATE` for high-volume logs

### Performance Impact
1. Use async logging for high-throughput applications
2. Set appropriate log levels for production
3. Monitor disk I/O impact

## Development

For development, use rich console logging:
```bash
export ENABLE_RICH_LOGGING=true
export LOG_LEVEL=DEBUG
```

For production, use structured logging:
```bash
export ENABLE_STRUCTURED_LOGGING=true
export LOG_LEVEL=INFO
export LOG_SAMPLING_RATE=0.1