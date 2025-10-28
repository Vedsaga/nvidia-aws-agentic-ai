#!/bin/bash
set -e

echo "Packaging Lambda functions..."

# Create package directory
rm -rf package lambda.zip
mkdir -p package

# Install dependencies
pip install -r requirements.txt -t package/

# Copy source code
cp -r src package/
cp -r lambda package/

# Create zip
cd package
zip -r ../lambda.zip . -x "*.pyc" -x "*__pycache__*"
cd ..

echo "Lambda package created: lambda.zip"
echo "Size: $(du -h lambda.zip | cut -f1)"
