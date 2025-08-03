#!/bin/bash

# Simplified Vector Search Deployment Script
# Works with current gcloud CLI versions and handles common issues

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
    
    echo $bucket_name
}

# Create sample embeddings data
create_sample_data() {
    local bucket_name=$1
    
    log_info "Creating sample embeddings data..."
    
    # Create sample data with proper 768-dimensional embeddings
    python3 -c "
import json
import random

def generate_sample_embedding():
    return [random.uniform(-0.1, 0.1) for _ in range(768)]

sample_data = [
    {
        'id': 'product_1', 
        'embedding': generate_sample_embedding(),
        'restricts': [{'namespace': 'category', 'allow': ['electronics']}]
    },
    {
        'id': 'product_2', 
        'embedding': generate_sample_embedding(),
        'restricts': [{'namespace': 'category', 'allow': ['electronics']}]
    },
    {
        'id': 'product_3', 
        'embedding': generate_sample_embedding(),
        'restricts': [{'namespace': 'category', 'allow': ['clothing']}]
    },
    {
        'id': 'product_4', 
        'embedding': generate_sample_embedding(),
        'restricts': [{'namespace': 'category', 'allow': ['books']}]
    },
    {
        'id': 'product_5', 
        'embedding': generate_sample_embedding(),
        'restricts': [{'namespace': 'category', 'allow': ['home']}]
    }
]

with open('/tmp/sample-embeddings.jsonl', 'w') as f:
    for item in sample_data:
        f.write(json.dumps(item) + '\n')

print('Sample embeddings data created with 768 dimensions')
"
    
    # Compress and upload
    gzip /tmp/sample-embeddings.jsonl
    gsutil cp /tmp/sample-embeddings.jsonl.gz gs://$bucket_name/sample-data/
    
    log_success "Sample data uploaded to gs://$bucket_name/sample-data/"
    
    # Clean up
    rm -f /tmp/sample-embeddings.jsonl.gz
    
    echo "gs://$bucket_name/sample-data/sample-embeddings.jsonl.gz"
}

# Manual deployment instructions
show_manual_instructions() {
    local bucket_name=$1
    local sample_data_uri=$2
    
    log_info "Due to gcloud CLI version differences, please complete the deployment manually:"
    
    echo ""
    echo "=== MANUAL DEPLOYMENT STEPS ==="
    echo ""
    echo "1. Go to Google Cloud Console: https://console.cloud.google.com/vertex-ai/matching-engine/indexes"
    echo "   Project: $PROJECT_ID"
    echo "   Region: $LOCATION"
    echo ""
    echo "2. Create Vector Index:"
    echo "   - Click 'CREATE INDEX'"
    echo "   - Name: product-semantic-index-$ENVIRONMENT"
    echo "   - Description: Vector index for product semantic search"
    echo "   - Region: $LOCATION"
    echo "   - Dimensions: 768"
    echo "   - Distance measure: Cosine distance"
    echo "   - Algorithm: Tree-AH"
    echo "   - Leaf node embedding count: 500"
    echo "   - Leaf nodes to search percent: 7"
    echo "   - Update method: Batch update"
    echo ""
    echo "3. Upload Initial Data (optional for testing):"
    echo "   - After index is created, click 'UPDATE INDEX'"
    echo "   - Data source: Cloud Storage"
    echo "   - Path: $sample_data_uri"
    echo ""
    echo "4. Create Index Endpoint:"
    echo "   - Go to: https://console.cloud.google.com/vertex-ai/matching-engine/index-endpoints"
    echo "   - Click 'CREATE ENDPOINT'"
    echo "   - Name: product-search-endpoint-$ENVIRONMENT"
    echo "   - Region: $LOCATION"
    echo "   - Network: Default"
    echo ""
    echo "5. Deploy Index to Endpoint:"
    echo "   - After both index and endpoint are ready"
    echo "   - Go to your endpoint"
    echo "   - Click 'DEPLOY INDEX'"
    echo "   - Select your index"
    echo "   - Deployed index ID: product_search_v1_$ENVIRONMENT"
    echo "   - Machine type: n1-standard-2"
    echo "   - Min replicas: 1"
    echo "   - Max replicas: 3"
    echo ""
    echo "=== CONFIGURATION FOR YOUR APPLICATION ==="
    echo ""
    echo "After manual deployment, update your application configuration:"
    echo ""
    echo "# In your Python code:"
    echo "vector_search_service.default_endpoint_name = 'product-search-endpoint-$ENVIRONMENT'"
    echo "vector_search_service.default_deployed_index_id = 'product_search_v1_$ENVIRONMENT'"
    echo ""
    echo "# Get the actual IDs from the console and update:"
    echo "# ENDPOINT_ID = 'projects/$PROJECT_ID/locations/$LOCATION/indexEndpoints/YOUR_ENDPOINT_ID'"
    echo "# INDEX_ID = 'projects/$PROJECT_ID/locations/$LOCATION/indexes/YOUR_INDEX_ID'"
    echo ""
}

# Test the setup
test_setup() {
    log_info "Testing Python dependencies..."
    
    # Check if Python dependencies are available
    python3 -c "
try:
    import json
    import random
    print('✓ Python dependencies OK')
except ImportError as e:
    print(f'✗ Missing Python dependency: {e}')
    exit(1)
"
    
    log_info "Testing Google Cloud access..."
    
    # Test basic gcloud access
    if gcloud projects describe $PROJECT_ID &>/dev/null; then
        log_success "✓ Google Cloud project access OK"
    else
        log_error "✗ Cannot access project $PROJECT_ID"
        exit 1
    fi
    
    # Test storage access
    if gsutil ls gs:// &>/dev/null; then
        log_success "✓ Google Cloud Storage access OK"
    else
        log_error "✗ Cannot access Google Cloud Storage"
        exit 1
    fi
}

# Main function
main() {
    log_info "Starting Simplified Vector Search deployment for project: $PROJECT_ID"
    log_info "Environment: $ENVIRONMENT"
    log_info "Location: $LOCATION"
    
    # Test setup
    test_setup
    
    # Check prerequisites
    check_prerequisites
    
    # Create storage bucket
    local bucket_name=$(create_storage_bucket)
    
    # Create sample data if requested
    local sample_data_uri=""
    if [ "$1" = "--with-sample-data" ]; then
        sample_data_uri=$(create_sample_data $bucket_name)
    fi
    
    # Show manual instructions
    show_manual_instructions $bucket_name $sample_data_uri
    
    log_success "Setup completed! Please follow the manual instructions above."
    
    # Create a summary file
    cat > deployment-info.txt << EOF
Vector Search Deployment Information
===================================

Project ID: $PROJECT_ID
Environment: $ENVIRONMENT
Location: $LOCATION
Storage Bucket: $bucket_name
Sample Data URI: $sample_data_uri

Manual deployment required due to gcloud CLI compatibility issues.
Please follow the instructions shown above.

Next Steps:
1. Complete manual deployment in Google Cloud Console
2. Update your application configuration with the actual resource IDs
3. Test the vector search functionality
4. Generate embeddings for your product catalog

Configuration Files:
- Vector Index Config: backend/infra/vector-index.yaml
- Service Implementation: backend/src/infinitum/infrastructure/external_services/
- Tests: backend/tests/test_vector_search.py
- Examples: backend/examples/vector_search_example.py
- Documentation: backend/docs/vector-search-guide.md
EOF
    
    log_success "Deployment information saved to deployment-info.txt"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Simplified Vector Search Deployment Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --with-sample-data    Create sample data for testing"
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