# Kāraka RAG System - NVIDIA AWS AI Agent Hackathon

A semantic knowledge graph system using NVIDIA NIM models and AWS infrastructure to extract and query Kāraka (semantic role) relationships from text.

## 🎯 Hackathon Submission

**Important**: According to contest rules, you only need credits for development, testing, and creating your video. The app does NOT need to remain deployed during judging. Judges will deploy using their own AWS credentials following these instructions.

## 📋 Quick Start for Judges

### Prerequisites
- AWS Account with credentials
- Python 3.8+
- Docker (optional, for local testing)

### Option 1: Local Testing (Recommended First)

```bash
# Lightweight mode (no Docker required)
python deploy_local.py --lightweight

# Or full mode with Docker
python deploy_local.py
```

### Option 2: AWS Deployment

1. **Configure AWS credentials** in `.env.vocareum` or `.env.personal`:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_SESSION_TOKEN=your_token  # if using temporary credentials
AWS_REGION=us-east-1
```

2. **Validate configuration**:
```bash
python deploy_server.py --env vocareum --validate-only
```

3. **Deploy to AWS** (takes 15-20 minutes):
```bash
python deploy_server.py --env vocareum
```

4. **Test the deployment**:
```bash
python test_e2e.py --mode server
```

5. **Cleanup when done** (important to avoid charges):
```bash
python deploy_server.py --env vocareum --destroy
```

## 🏗️ Architecture

```
API Gateway → Lambda Functions → SageMaker Endpoints (NVIDIA NIM)
                ↓                        ↓
            Neo4j Graph              • Nemotron Nano 8B
            (EC2)                    • Embedding NIM
```

## 📦 Project Structure

```
.
├── deploy_local.py          # Local deployment script
├── deploy_server.py         # AWS deployment script
├── test_e2e.py             # End-to-end testing
├── src/                    # Source code
│   ├── lambda/            # Lambda function handlers
│   ├── karaka/            # Kāraka extraction logic
│   └── utils/             # Utilities
├── infrastructure/         # AWS infrastructure code
├── frontend/              # Web UI
└── data/                  # Sample test data
```

## 🚀 Deployment Scripts

### 1. `deploy_local.py`
Local development deployment with hardware validation.

**Usage:**
```bash
python deploy_local.py                    # Full setup with Docker
python deploy_local.py --lightweight      # Lightweight mode (no Docker)
python deploy_local.py --destroy          # Cleanup
```

**Features:**
- Hardware requirements check (CPU, RAM, disk, GPU)
- Virtual environment setup
- Docker Compose management (Neo4j, NIM models)
- Lightweight mode using local Python models

### 2. `deploy_server.py`
AWS server deployment with validation.

**Usage:**
```bash
python deploy_server.py --env vocareum              # Deploy to Vocareum
python deploy_server.py --env personal              # Deploy to personal AWS
python deploy_server.py --validate-only             # Validate config only
python deploy_server.py --destroy                   # Cleanup resources
```

**Deploys:**
- SageMaker endpoints (Nemotron + Embedding)
- Lambda functions (ingestion, query, graph, status)
- API Gateway (REST API)
- Neo4j on EC2
- S3 bucket for data storage

### 3. `test_e2e.py`
End-to-end testing for both local and server deployments.

**Usage:**
```bash
python test_e2e.py --mode local     # Test local deployment
python test_e2e.py --mode server    # Test server deployment
```

**Tests:**
- Document upload and ingestion
- Graph structure verification
- Query processing with Kāraka validation
- API endpoint functionality

## 🔧 Configuration

All configuration is in `.env` files:

- `.env.example` - Template with all options
- `.env.vocareum` - Vocareum lab credentials
- `.env.personal` - Personal AWS account
- `.env.local` - Local development
- `.env.lightweight` - Lightweight local mode

**Key Configuration:**
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# SageMaker Configuration
SAGEMAKER_NEMOTRON_ENDPOINT=nemotron-karaka-endpoint
SAGEMAKER_EMBEDDING_ENDPOINT=embedding-karaka-endpoint
SAGEMAKER_INSTANCE_TYPE=ml.g5.xlarge

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=hackathon2025
```

## 🧪 Testing

### Local Testing
```bash
# Start local environment
python deploy_local.py

# Run tests
python test_e2e.py --mode local
```

### Server Testing
```bash
# Deploy to AWS
python deploy_server.py --env vocareum

# Run tests
python test_e2e.py --mode server

# Cleanup
python deploy_server.py --env vocareum --destroy
```

## 💰 Cost Estimation

### Local Development
- **Cost**: $0 (runs on your machine)
- **Time**: 5-10 minutes setup

### AWS Deployment (per hour)
- SageMaker (ml.g5.xlarge × 2): ~$1.50/hour
- EC2 (t3.micro): ~$0.01/hour
- Lambda: ~$0.20 per 1M requests
- API Gateway: ~$3.50 per 1M requests
- S3: ~$0.023 per GB

**Estimated cost for testing**: $5-10 for a few hours

**⚠️ Important**: Always run cleanup when done to avoid charges!

## 🎓 Hackathon Compliance

This project meets all NVIDIA AWS AI Agent Hackathon requirements:

✅ Uses NVIDIA NIM Llama 3.1 Nemotron Nano 8B V1  
✅ Uses NVIDIA Retrieval Embedding NIM  
✅ Deployed on AWS SageMaker (ml.g5.xlarge)  
✅ Includes deployment instructions for judges  
✅ All configuration in `.env` files  
✅ Easy cleanup to avoid charges  
✅ Public code repository  
✅ Video demonstration included  

## 🔍 API Endpoints

After deployment, the following endpoints are available:

- `POST /ingest` - Upload and process documents
- `GET /ingest/status/{job_id}` - Check ingestion status
- `POST /query` - Query the knowledge graph
- `GET /graph` - Get graph visualization data
- `GET /health` - Health check

## 🐛 Troubleshooting

### AWS Credentials Expired
```bash
# Get fresh credentials from Vocareum "Cloud access" section
# Update .env.vocareum
# Validate again
python deploy_server.py --env vocareum --validate-only
```

### SageMaker Deployment Fails
- Check AWS service quotas
- Ensure permissions for SageMaker endpoints
- Try different region if capacity issues

### Docker Issues (Local)
```bash
# Check Docker is running
docker ps

# Restart Docker Desktop
# Try lightweight mode instead
python deploy_local.py --lightweight
```

## 📚 Additional Resources

- **NVIDIA NIM Documentation**: https://docs.nvidia.com/nim/
- **AWS SageMaker**: https://aws.amazon.com/sagemaker/
- **Neo4j Graph Database**: https://neo4j.com/docs/

## 📝 License

This project is submitted for the NVIDIA AWS AI Agent Hackathon.

## 🤝 Support

For issues during judging:
1. Verify AWS credentials are current
2. Check CloudWatch logs for Lambda errors
3. Ensure all prerequisites are installed
4. Try local testing first before AWS deployment

---

**Note for Judges**: All deployment scripts are self-contained Python files. No bash scripts required. Configuration is straightforward via `.env` files. The system can be deployed and tested in under 30 minutes.
