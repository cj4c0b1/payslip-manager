#!/bin/bash
set -e

# This script runs during the build process on Streamlit Cloud

echo "🚀 Setting up Payslip Manager on Streamlit Cloud..."

# Create necessary directories
mkdir -p ./data
mkdir -p ./uploads
mkdir -p ./logs

# Set permissions for Streamlit Cloud
chmod 755 ./data
chmod 755 ./uploads
chmod 755 ./logs

# Install dependencies from requirements.txt
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install the package in development mode
echo "🔧 Installing package in development mode..."
pip install -e .

# Initialize the database if it doesn't exist
if [ ! -f "./data/payslips.db" ]; then
    echo "💾 Initializing database..."
    python -c "from src.database import init_db; init_db()"
else
    echo "ℹ️  Database already exists, skipping initialization"
fi

echo "✅ Streamlit Cloud setup complete!"

exit 0
