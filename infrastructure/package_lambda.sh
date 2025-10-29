#!/bin/bash

# Lambda Packaging Script for Kāraka RAG System
# This script packages all dependencies and source code for AWS Lambda deployment

set -e  # Exit on error

echo "Starting Lambda packaging process..."

# Clean up previous builds
echo "Cleaning up previous builds..."
rm -rf package
rm -f lambda.zip

# Create package directory
echo "Creating package directory..."
mkdir -p package

# Install Python dependencies to package directory
echo "Installing Python dependencies..."
# Install all dependencies including spaCy
pip install -r requirements.txt -t package/ --upgrade --only-binary=:all:

# Download spaCy model directly
echo "Downloading spaCy model..."
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl -t package/

# Copy source modules to package
echo "Copying source modules..."
cp -r src/ package/

# Copy Lambda handlers to package
echo "Copying Lambda handlers..."
cp lambda/*.py package/

# Create deployment package
echo "Creating lambda.zip..."
cd package
zip -r ../lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h lambda.zip | cut -f1)
echo "Lambda package created successfully!"
echo "Package size: $PACKAGE_SIZE"

# Check if package is too large (Lambda limit is 50MB zipped, 250MB unzipped)
PACKAGE_SIZE_BYTES=$(stat -f%z lambda.zip 2>/dev/null || stat -c%s lambda.zip 2>/dev/null)
if [ $PACKAGE_SIZE_BYTES -gt 52428800 ]; then
    echo "WARNING: Package size exceeds 50MB. Consider using Lambda layers."
fi

echo "Packaging complete! lambda.zip is ready for deployment."
