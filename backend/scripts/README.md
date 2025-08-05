# Scripts

This directory contains deployment and utility scripts for the project.

## Structure

- [`deploy/`](deploy/) - Deployment scripts
  - [`deploy-cloud-run.sh`](deploy/deploy-cloud-run.sh) - Deploy to Google Cloud Run
  - [`deploy-vector-search.sh`](deploy/deploy-vector-search.sh) - Deploy vector search infrastructure
  - [`deploy-vector-search-simple.sh`](deploy/deploy-vector-search-simple.sh) - Simplified vector search deployment
- [`utils/`](utils/) - Utility scripts
  - [`test-vector-deployment.py`](utils/test-vector-deployment.py) - Test vector search deployment

## Usage

### Deployment Scripts

All deployment scripts should be run from the backend root directory:

```bash
# Deploy to Cloud Run
./scripts/deploy/deploy-cloud-run.sh

# Deploy vector search (full)
./scripts/deploy/deploy-vector-search.sh

# Deploy vector search (simplified)
./scripts/deploy/deploy-vector-search-simple.sh --with-sample-data
```

### Utility Scripts

```bash
# Test vector search deployment
python scripts/utils/test-vector-deployment.py
```

## Prerequisites

Before running deployment scripts, ensure you have:

1. **Environment Variables**: Set up in [`../config/.env`](../config/.env)
2. **GCP Credentials**: Configured in [`../credentials/`](../credentials/)
3. **Dependencies**: Install with `pip install -r requirements.txt`
4. **GCloud CLI**: Authenticated and configured

## Script Permissions

Make scripts executable:
```bash
chmod +x scripts/deploy/*.sh
```

## Environment Configuration

Scripts use configuration from:
- [`../config/.env`](../config/.env) - Main environment variables
- [`../config/.env.docker`](../config/.env.docker) - Docker-specific settings
- [`../config/.env.infra`](../config/.env.infra) - Infrastructure settings

## Troubleshooting

If deployment fails, check:
1. [`../docs/deployment/troubleshooting.md`](../docs/deployment/troubleshooting.md) - Common issues
2. [`../logs/`](../logs/) - Application logs
3. GCP Console - Cloud Run and Vertex AI status

## Adding New Scripts

When adding new scripts:
1. Place them in the appropriate subdirectory
2. Make them executable (`chmod +x`)
3. Add documentation to this README
4. Include error handling and logging
5. Use relative paths from backend root