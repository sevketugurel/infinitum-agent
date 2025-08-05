# Infrastructure

This directory contains all infrastructure-as-code and deployment configurations.

## Structure

- [`docker/`](docker/) - Docker configurations
  - [`Dockerfile`](docker/Dockerfile) - Application container definition
  - [`docker-compose.yml`](docker/docker-compose.yml) - Multi-container setup
  - [`.dockerignore`](docker/.dockerignore) - Docker build exclusions
- [`terraform/`](terraform/) - Terraform infrastructure definitions
  - [`cloud-run.tf`](terraform/cloud-run.tf) - Google Cloud Run configuration
  - [`.terraform.lock.hcl`](terraform/.terraform.lock.hcl) - Terraform dependency lock
- [`gcp/`](gcp/) - Google Cloud Platform specific configurations
  - [`cloud-run-service.yaml`](gcp/cloud-run-service.yaml) - Cloud Run service definition
  - [`vector-index.yaml`](gcp/vector-index.yaml) - Vector search index configuration
- [`kubernetes/`](kubernetes/) - Kubernetes manifests (future use)

## Quick Start

### Docker Development
```bash
cd infrastructure/docker
docker-compose up -d
```

### Terraform Deployment
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### GCP Direct Deployment
```bash
# Deploy to Cloud Run
gcloud run services replace infrastructure/gcp/cloud-run-service.yaml

# Create vector index
gcloud ai indexes create --config=infrastructure/gcp/vector-index.yaml
```

## Environment Configuration

Environment-specific configurations are stored in [`../config/`](../config/):
- `.env` - Main environment variables
- `.env.docker` - Docker-specific overrides
- `.env.infra` - Infrastructure-specific settings

## Notes

- All infrastructure components are designed to work together
- Use the deployment scripts in [`../scripts/deploy/`](../scripts/deploy/) for automated deployment
- Check [`../docs/deployment/`](../docs/deployment/) for detailed deployment guides