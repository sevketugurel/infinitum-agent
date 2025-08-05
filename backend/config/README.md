# Configuration

This directory contains all configuration files for the application.

## Files

- [`.env`](.env) - Main environment variables (not in git)
- [`.env.example`](.env.example) - Template for environment variables
- [`.env.docker`](.env.docker) - Docker-specific environment overrides
- [`.env.infra`](.env.infra) - Infrastructure-specific settings

## Setup

1. **Copy the example file**:
   ```bash
   cp config/.env.example config/.env
   ```

2. **Update with your values**:
   - Set your GCP project ID
   - Add API keys (Gemini, SerpAPI, etc.)
   - Configure logging preferences
   - Set monitoring options

## Environment Variables

### Core Configuration
- `ENVIRONMENT` - Application environment (development/production)
- `PORT` - Application port (default: 8080)

### GCP Configuration
- `GCP_PROJECT_ID` - Google Cloud Project ID
- `FIREBASE_PROJECT_ID` - Firebase Project ID
- `GOOGLE_CLOUD_PROJECT` - Google Cloud Project (usually same as GCP_PROJECT_ID)

### API Keys
- `GEMINI_API_KEY` - Google Gemini API key
- `GOOGLE_API_KEY` - Google API key
- `SERPAPI_API_KEY` - SerpAPI key for search functionality

### Logging Configuration
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)
- `LOG_FILE_PATH` - Path to log file
- `ENABLE_STRUCTURED_LOGGING` - Enable structured JSON logging
- `ENABLE_RICH_LOGGING` - Enable rich console logging
- `LOG_SAMPLING_RATE` - Log sampling rate (0.0-1.0)

### Monitoring
- `ENABLE_METRICS` - Enable Prometheus metrics
- `METRICS_PORT` - Metrics endpoint port
- `ENABLE_TRACING` - Enable distributed tracing
- `SENTRY_DSN` - Sentry error tracking DSN (optional)

### Performance
- `ENABLE_PERFORMANCE_LOGGING` - Log performance metrics
- `LOG_SLOW_OPERATIONS` - Log slow operations
- `SLOW_OPERATION_THRESHOLD` - Threshold for slow operations (seconds)

## Security Notes

- **Never commit `.env` files** - They contain sensitive information
- **Use `.env.example`** - For documenting required variables
- **Rotate API keys regularly** - Especially in production
- **Use different keys** - For different environments

## Docker Configuration

The `.env.docker` file contains Docker-specific overrides:
- Container-specific paths
- Docker network settings
- Volume mount configurations

## Infrastructure Configuration

The `.env.infra` file contains infrastructure-specific settings:
- Terraform variables
- Deployment configurations
- Cloud-specific settings

## Loading Order

Environment variables are loaded in this order (later values override earlier ones):
1. System environment variables
2. `.env.infra` (infrastructure settings)
3. `.env.docker` (Docker overrides)
4. `.env` (main configuration)

## Validation

The application validates required environment variables on startup. Check the logs if you encounter configuration errors.