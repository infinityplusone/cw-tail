#!/bin/bash
set -e

echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
   
# Install required dependencies (boto3 and python-dotenv)
echo "Installing dependencies..."
pip install --upgrade boto3 python-dotenv

# Install the package
echo "Installing the package..."
pip install -e .

echo "Installation complete!"

echo ""

echo "To activate the virtual environment, run:"
echo "source env/bin/activate  # On Windows: env\Scripts\activate"

echo ""

echo "To run the tool, run:"
echo "cw-tail --help"

echo ""

echo "To deactivate the virtual environment, run:"
echo "deactivate"

echo ""
