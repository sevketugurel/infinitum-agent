# Infinitum AI Agent Backend

A production-ready FastAPI backend for the Infinitum AI Agent with advanced vector search, semantic analysis, and intelligent product recommendations.

## 🚀 Quick Start

### Prerequisites
- Python 3.11-3.13
- Google Cloud Platform account
- API keys (Gemini, SerpAPI)

### Setup
1. **Clone and navigate**:
   ```bash
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your values
   ```

4. **Set up credentials**:
   ```bash
   # Place your GCP service account key in credentials/
   export GOOGLE_APPLICATION_CREDENTIALS="backend/credentials/your-key.json"
   ```

5. **Run the application**:
   ```bash
   python -m uvicorn src.infinitum.main:app --reload --port 8080
   ```

## 📁 Project Structure

```
backend/
├── README.md                    # This file
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Dependencies
├── Makefile                    # Build commands
│
├── config/                     # 🔧 Configuration files
│   ├── .env                    # Environment variables (not in git)
│   ├── .env.example           # Environment template
│   ├── .env.docker            # Docker-specific settings
│   ├── .env.infra             # Infrastructure settings
│   └── README.md              # Configuration guide
│
├── docs/                       # 📚 Documentation
│   ├── README.md              # Documentation index
│   ├── api/                   # API documentation
│   │   └── postman-collection.json
│   ├── deployment/            # Deployment guides
│   │   ├── vector-search-guide.md
│   │   └── troubleshooting.md
│   └── development/           # Development guides
│
├── infrastructure/             # 🏗️ Infrastructure as Code
│   ├── README.md              # Infrastructure guide
│   ├── docker/                # Docker configurations
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── .dockerignore
│   ├── terraform/             # Terraform configurations
│   │   ├── cloud-run.tf
│   │   └── .terraform.lock.hcl
│   ├── gcp/                   # GCP specific configs
│   │   ├── cloud-run-service.yaml
│   │   └── vector-index.yaml
│   └── kubernetes/            # K8s manifests (future)
│
├── scripts/                    # 🔨 Deployment & utility scripts
│   ├── README.md              # Scripts guide
│   ├── deploy/                # Deployment scripts
│   │   ├── deploy-cloud-run.sh
│   │   ├── deploy-vector-search.sh
│   │   └── deploy-vector-search-simple.sh
│   └── utils/                 # Utility scripts
│       └── test-vector-deployment.py
│
├── src/                        # 💻 Application source code
│   └── infinitum/
│       ├── main.py            # FastAPI application
│       ├── settings.py        # Application settings
│       ├── application/       # Use cases & business logic
│       ├── domain/            # Domain entities & services
│       ├── infrastructure/    # External services & persistence
│       └── interfaces/        # Contracts & abstractions
│
├── tests/                      # 🧪 Test files
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── dummy_data/            # Test data
│
├── examples/                   # 📖 Usage examples
│   └── vector_search_example.py
│
├── credentials/                # 🔐 Secure credentials
│   ├── .gitignore             # Protect credentials
│   └── README.md              # Credential setup guide
│
└── logs/                       # 📝 Application logs
    ├── .gitignore             # Ignore log files
    └── README.md              # Logging configuration
```

## 🎯 Key Features

### AI & Machine Learning
- **Vector Search**: Production-ready semantic search with Vertex AI
- **LLM Integration**: Gemini 2.5 Flash for intelligent responses
- **Embeddings Pipeline**: Batch processing with rate limiting
- **Semantic Analysis**: Advanced query understanding and enhancement

### Product Intelligence
- **Smart Search**: Hybrid semantic + keyword search
- **Recommendations**: Personalized product suggestions
- **Web Scraping**: Crawl4AI integration for product data
- **Package Creation**: Intelligent product bundling

### Production Features
- **Enhanced Logging**: Structured logging with rich console output
- **Monitoring**: Prometheus metrics and health checks
- **Caching**: Multi-level caching for performance
- **Error Handling**: Comprehensive error recovery
- **Authentication**: JWT-based security

### Infrastructure
- **Docker**: Multi-stage builds with optimization
- **Cloud Run**: Serverless deployment on GCP
- **Terraform**: Infrastructure as Code
- **Vector Search**: Scalable Vertex AI integration

## 🔧 Configuration

### Environment Variables
Key configuration in [`config/.env`](config/.env):
```bash
# Core
ENVIRONMENT=development
PORT=8080

# GCP
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=backend/credentials/your-key.json

# API Keys
GEMINI_API_KEY=your-gemini-key
SERPAPI_API_KEY=your-serpapi-key

# Logging
LOG_LEVEL=DEBUG
ENABLE_RICH_LOGGING=true
```

See [`config/README.md`](config/README.md) for complete configuration guide.

## 🚀 Deployment

### Local Development
```bash
# Using Docker
cd infrastructure/docker
docker-compose up -d

# Direct Python
python -m uvicorn src.infinitum.main:app --reload
```

### Production Deployment
```bash
# Deploy to Google Cloud Run
./scripts/deploy/deploy-cloud-run.sh

# Deploy vector search infrastructure
./scripts/deploy/deploy-vector-search.sh
```

See [`docs/deployment/`](docs/deployment/) for detailed deployment guides.

## 📊 API Endpoints

### Core Endpoints
- `GET /healthz` - Health check
- `POST /api/v1/chat` - AI chat interface
- `POST /api/v1/packages` - Create product packages
- `GET /api/v1/users/{id}/profile` - User management

### Admin Endpoints
- `GET /admin/logs/dashboard` - Logging dashboard
- `GET /metrics` - Prometheus metrics
- `POST /clear-cache` - Cache management

### Testing
Import [`docs/api/postman-collection.json`](docs/api/postman-collection.json) into Postman for complete API testing.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/test_vector_search.py

# Run with coverage
pytest --cov=src/infinitum
```

## 📚 Documentation

- **[API Documentation](docs/api/)** - Postman collection and API guides
- **[Deployment Guides](docs/deployment/)** - Production deployment instructions
- **[Vector Search Guide](docs/deployment/vector-search-guide.md)** - Comprehensive vector search setup
- **[Troubleshooting](docs/deployment/troubleshooting.md)** - Common issues and solutions

## 🏗️ Architecture

The backend follows Clean Architecture principles:

- **Domain Layer**: Core business logic and entities
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: External services and persistence
- **Interface Layer**: HTTP endpoints and contracts

### Key Components
- **Vector Search Service**: Semantic search with Vertex AI
- **LLM Service**: Gemini integration for AI responses
- **User Context Service**: Personalization and preferences
- **Package Service**: Intelligent product bundling
- **Logging System**: Structured logging with monitoring

## 🔐 Security

- **JWT Authentication**: Secure API access
- **Environment Variables**: Sensitive data protection
- **Credential Management**: Secure key storage
- **Input Validation**: Pydantic models for data validation
- **Rate Limiting**: API quota management

## 📈 Performance

- **Caching**: Multi-level caching strategy
- **Async Operations**: Non-blocking I/O
- **Connection Pooling**: Efficient resource usage
- **Batch Processing**: Optimized bulk operations
- **Monitoring**: Performance metrics and alerts

## 🤝 Contributing

1. **Setup Development Environment**:
   ```bash
   cp config/.env.example config/.env
   pip install -r requirements.txt
   ```

2. **Run Tests**:
   ```bash
   pytest
   ```

3. **Code Style**:
   ```bash
   black src/
   isort src/
   flake8 src/
   ```

## 📞 Support

- **Documentation**: Check [`docs/`](docs/) directory
- **Troubleshooting**: See [`docs/deployment/troubleshooting.md`](docs/deployment/troubleshooting.md)
- **Examples**: Review [`examples/`](examples/) directory
- **Logs**: Check [`logs/`](logs/) directory for debugging

## 🔄 Recent Changes

This backend has been recently reorganized for better maintainability:
- ✅ Improved directory structure
- ✅ Centralized configuration management
- ✅ Enhanced documentation
- ✅ Streamlined deployment process
- ✅ Better security practices

See [`REORGANIZATION_PLAN.md`](REORGANIZATION_PLAN.md) for details on the structural improvements.

---

**Built with FastAPI, Vertex AI, and modern Python practices for production-scale AI applications.**