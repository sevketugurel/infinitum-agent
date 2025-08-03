#!/bin/bash

# Vector Search Deployment Script
# Automates the deployment of Vertex AI Vector Search infrastructure

set -e  # Exit on any error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-infinitum-agent}"
LOCATION="${GCP_LOCATION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Check if project is set
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        log_warning "Current project is $CURRENT_PROJECT, switching to $PROJECT_ID"
        gcloud config set project $PROJECT_ID
    fi
    
    # Check if required APIs are enabled
    log_info "Checking required APIs..."
    REQUIRED_APIS=(
        "aiplatform.googleapis.com"
        "storage.googleapis.com"
        "compute.googleapis.com"
    )
    
    for api in "${REQUIRED_APIS[@]}"; do
        if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            log_info "Enabling API: $api"
            gcloud services enable $api
        else
            log_success "API already enabled: $api"
        fi
    done
    
    log_success "Prerequisites check completed"
}

# Create GCS bucket for embeddings data
create_storage_bucket() {
    local bucket_name="$PROJECT_ID-vector-embeddings"
    
    log_info "Creating GCS bucket: $bucket_name"
    
    if gsutil ls -b gs://$bucket_name &>/dev/null; then
        log_warning "Bucket already exists: $bucket_name"
    else
        gsutil mb -p $PROJECT_ID -c STANDARD -l $LOCATION gs://$bucket_name
        log_success "Created bucket: $bucket_name"
    fi
    
    # Set appropriate permissions
    gsutil iam ch serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com:objectAdmin gs://$bucket_name
    
    echo $bucket_name
}

# Deploy vector index
deploy_vector_index() {
    local index_name="product-semantic-index-$ENVIRONMENT"
    local bucket_name=$1
    
    log_info "Deploying vector index: $index_name"
    
    # Check if index already exists
    if gcloud ai indexes list --region=$LOCATION --filter="displayName:$index_name" --format="value(name)" | grep -q .; then
        log_warning "Index already exists: $index_name"
        local existing_index=$(gcloud ai indexes list --region=$LOCATION --filter="displayName:$index_name" --format="value(name)" | head -1)
        echo $existing_index
        return
    fi
    
    # Create index configuration file
    cat > /tmp/index-config.json << EOF
{
  "displayName": "$index_name",
  "description": "Vector index for product semantic search - $ENVIRONMENT",
  "metadata": {
    "config": {
      "dimensions": 768,
      "approximateNeighborsCount": 150,
      "distanceMeasureType": "COSINE_DISTANCE",
      "algorithmConfig": {
        "treeAhConfig": {
          "leafNodeEmbeddingCount": 500,
          "leafNodesToSearchPercent": 7
        }
      }
    }
  },
  "indexUpdateMethod": "BATCH_UPDATE",
  "labels": {
    "environment": "$ENVIRONMENT",
    "use-case": "product-search",
    "created-by": "deployment-script"
  }
}
EOF
    
    # Create the index
    log_info "Creating vector index (this may take 30-60 minutes)..."
    local index_operation=$(gcloud ai indexes create \
        --region=$LOCATION \
        --display-name="$index_name" \
        --description="Vector index for product semantic search - $ENVIRONMENT" \
        --config-file=/tmp/index-config.json \
        --format="value(name)")
    
    if [ -n "$index_operation" ]; then
        log_info "Index creation started. Operation: $index_operation"
        
        # Wait for operation to complete
        log_info "Waiting for index creation to complete..."
        gcloud ai operations wait $index_operation --region=$LOCATION
        
        # Get the created index
        local index_id=$(gcloud ai operations describe $index_operation --region=$LOCATION --format="value(response.name)")
        log_success "Vector index created: $index_id"
        echo $index_id
    else
        log_error "Failed to create vector index"
        exit 1
    fi
    
    # Clean up temp file
    rm -f /tmp/index-config.json
}

# Deploy index endpoint
deploy_index_endpoint() {
    local endpoint_name="product-search-endpoint-$ENVIRONMENT"
    
    log_info "Deploying index endpoint: $endpoint_name"
    
    # Check if endpoint already exists
    if gcloud ai index-endpoints list --region=$LOCATION --filter="displayName:$endpoint_name" --format="value(name)" | grep -q .; then
        log_warning "Endpoint already exists: $endpoint_name"
        local existing_endpoint=$(gcloud ai index-endpoints list --region=$LOCATION --filter="displayName:$endpoint_name" --format="value(name)" | head -1)
        echo $existing_endpoint
        return
    fi
    
    # Create the endpoint
    log_info "Creating index endpoint..."
    local endpoint_operation=$(gcloud ai index-endpoints create \
        --region=$LOCATION \
        --display-name="$endpoint_name" \
        --description="Endpoint for product semantic search - $ENVIRONMENT" \
        --format="value(name)")
    
    if [ -n "$endpoint_operation" ]; then
        log_info "Endpoint creation started. Operation: $endpoint_operation"
        
        # Wait for operation to complete
        gcloud ai operations wait $endpoint_operation --region=$LOCATION
        
        # Get the created endpoint
        local endpoint_id=$(gcloud ai operations describe $endpoint_operation --region=$LOCATION --format="value(response.name)")
        log_success "Index endpoint created: $endpoint_id"
        echo $endpoint_id
    else
        log_error "Failed to create index endpoint"
        exit 1
    fi
}

# Deploy index to endpoint
deploy_index_to_endpoint() {
    local index_id=$1
    local endpoint_id=$2
    local deployed_index_id="product-search-v1-$ENVIRONMENT"
    
    log_info "Deploying index to endpoint..."
    log_info "Index: $index_id"
    log_info "Endpoint: $endpoint_id"
    log_info "Deployed Index ID: $deployed_index_id"
    
    # Check if already deployed
    if gcloud ai index-endpoints describe $endpoint_id --region=$LOCATION --format="value(deployedIndexes[].id)" | grep -q "$deployed_index_id"; then
        log_warning "Index already deployed to endpoint with ID: $deployed_index_id"
        return
    fi
    
    # Deploy the index
    local deploy_operation=$(gcloud ai index-endpoints deploy-index $endpoint_id \
        --region=$LOCATION \
        --index=$index_id \
        --deployed-index-id=$deployed_index_id \
        --display-name="Product Search Deployment v1 - $ENVIRONMENT" \
        --machine-type=n1-standard-2 \
        --min-replica-count=1 \
        --max-replica-count=3 \
        --format="value(name)")
    
    if [ -n "$deploy_operation" ]; then
        log_info "Index deployment started. Operation: $deploy_operation"
        
        # Wait for operation to complete (this can take 10-20 minutes)
        log_info "Waiting for index deployment to complete (this may take 10-20 minutes)..."
        gcloud ai operations wait $deploy_operation --region=$LOCATION
        
        log_success "Index successfully deployed to endpoint"
    else
        log_error "Failed to deploy index to endpoint"
        exit 1
    fi
}

# Create sample embeddings data
create_sample_data() {
    local bucket_name=$1
    
    log_info "Creating sample embeddings data..."
    
    # Create sample data file
    cat > /tmp/sample-embeddings.jsonl << 'EOF'
{"id": "product_1", "embedding": [0.1, 0.2, 0.3, 0.4, 0.5], "restricts": [{"namespace": "category", "allow": ["electronics"]}]}
{"id": "product_2", "embedding": [0.2, 0.3, 0.4, 0.5, 0.6], "restricts": [{"namespace": "category", "allow": ["electronics"]}]}
{"id": "product_3", "embedding": [0.3, 0.4, 0.5, 0.6, 0.7], "restricts": [{"namespace": "category", "allow": ["clothing"]}]}
EOF
    
    # Note: This is just sample data with 5 dimensions for testing
    # In production, you would use 768-dimensional embeddings from your actual products
    
    # Compress and upload
    gzip /tmp/sample-embeddings.jsonl
    gsutil cp /tmp/sample-embeddings.jsonl.gz gs://$bucket_name/sample-data/
    
    log_success "Sample data uploaded to gs://$bucket_name/sample-data/"
    
    # Clean up
    rm -f /tmp/sample-embeddings.jsonl.gz
    
    echo "gs://$bucket_name/sample-data/sample-embeddings.jsonl.gz"
}

# Update index with sample data
update_index_with_data() {
    local index_id=$1
    local data_uri=$2
    
    log_info "Updating index with sample data..."
    log_info "Index: $index_id"
    log_info "Data URI: $data_uri"
    
    # Update the index with embeddings data
    local update_operation=$(gcloud ai indexes update $index_id \
        --region=$LOCATION \
        --contents-delta-uri=$data_uri \
        --format="value(name)")
    
    if [ -n "$update_operation" ]; then
        log_info "Index update started. Operation: $update_operation"
        
        # Wait for operation to complete
        log_info "Waiting for index update to complete..."
        gcloud ai operations wait $update_operation --region=$LOCATION
        
        log_success "Index updated with sample data"
    else
        log_error "Failed to update index with data"
        exit 1
    fi
}

# Create deployment summary
create_deployment_summary() {
    local bucket_name=$1
    local index_id=$2
    local endpoint_id=$3
    local deployed_index_id="product-search-v1-$ENVIRONMENT"
    
    log_info "Creating deployment summary..."
    
    cat > deployment-summary.json << EOF
{
  "deployment_info": {
    "project_id": "$PROJECT_ID",
    "location": "$LOCATION",
    "environment": "$ENVIRONMENT",
    "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  },
  "resources": {
    "storage_bucket": "$bucket_name",
    "vector_index": {
      "id": "$index_id",
      "name": "product-semantic-index-$ENVIRONMENT"
    },
    "index_endpoint": {
      "id": "$endpoint_id",
      "name": "product-search-endpoint-$ENVIRONMENT"
    },
    "deployed_index": {
      "id": "$deployed_index_id",
      "display_name": "Product Search Deployment v1 - $ENVIRONMENT"
    }
  },
  "configuration": {
    "dimensions": 768,
    "distance_measure": "COSINE_DISTANCE",
    "machine_type": "n1-standard-2",
    "min_replicas": 1,
    "max_replicas": 3
  },
  "next_steps": [
    "Update your application configuration with the endpoint ID",
    "Generate and upload your actual product embeddings",
    "Test the search functionality",
    "Monitor performance and costs"
  ]
}
EOF
    
    log_success "Deployment summary created: deployment-summary.json"
}

# Verify deployment
verify_deployment() {
    local endpoint_id=$1
    local deployed_index_id="product-search-v1-$ENVIRONMENT"
    
    log_info "Verifying deployment..."
    
    # Check endpoint status
    local endpoint_status=$(gcloud ai index-endpoints describe $endpoint_id --region=$LOCATION --format="value(deployedIndexes[0].privateEndpoints.serviceAttachment)")
    
    if [ -n "$endpoint_status" ]; then
        log_success "Endpoint is active and ready"
    else
        log_warning "Endpoint may not be fully ready yet"
    fi
    
    # List deployed indexes
    log_info "Deployed indexes:"
    gcloud ai index-endpoints describe $endpoint_id --region=$LOCATION --format="table(deployedIndexes[].id,deployedIndexes[].displayName,deployedIndexes[].createTime)"
}

# Main deployment function
main() {
    log_info "Starting Vector Search deployment for project: $PROJECT_ID"
    log_info "Environment: $ENVIRONMENT"
    log_info "Location: $LOCATION"
    
    # Check prerequisites
    check_prerequisites
    
    # Create storage bucket
    local bucket_name=$(create_storage_bucket)
    
    # Deploy vector index
    local index_id=$(deploy_vector_index $bucket_name)
    
    # Deploy index endpoint
    local endpoint_id=$(deploy_index_endpoint)
    
    # Create sample data (optional for testing)
    if [ "$ENVIRONMENT" = "development" ] || [ "$1" = "--with-sample-data" ]; then
        local sample_data_uri=$(create_sample_data $bucket_name)
        update_index_with_data $index_id $sample_data_uri
    fi
    
    # Deploy index to endpoint
    deploy_index_to_endpoint $index_id $endpoint_id
    
    # Create deployment summary
    create_deployment_summary $bucket_name $index_id $endpoint_id
    
    # Verify deployment
    verify_deployment $endpoint_id
    
    log_success "Vector Search deployment completed successfully!"
    log_info "Check deployment-summary.json for details and next steps"
    
    # Display important information
    echo ""
    echo "=== DEPLOYMENT SUMMARY ==="
    echo "Project ID: $PROJECT_ID"
    echo "Environment: $ENVIRONMENT"
    echo "Storage Bucket: $bucket_name"
    echo "Vector Index ID: $index_id"
    echo "Index Endpoint ID: $endpoint_id"
    echo "Deployed Index ID: product-search-v1-$ENVIRONMENT"
    echo ""
    echo "Update your application with these values!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Vector Search Deployment Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --with-sample-data    Include sample data for testing"
        echo "  --help, -h           Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  GCP_PROJECT_ID       Google Cloud Project ID (default: infinitum-agent)"
        echo "  GCP_LOCATION         Google Cloud Location (default: us-central1)"
        echo "  ENVIRONMENT          Deployment environment (default: production)"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac