#!/bin/bash

# Setup script for Karaka RAG System
# Installs all dependencies at project level

set -e

echo "🚀 Setting up Karaka RAG System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements (using --no-build-isolation to avoid compilation issues)
echo "📥 Installing Python dependencies..."
pip install spacy --no-build-isolation
pip install neo4j boto3 python-dotenv requests numpy

# Download spaCy model
echo "🧠 Downloading spaCy model (en_core_web_sm)..."
python -m spacy download en_core_web_sm

# Clean up pycache
echo "🧹 Cleaning up __pycache__ directories..."
find ./src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find ./src -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To test the SRL Parser, run:"
echo "  python test_srl_parser.py"
