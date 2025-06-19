#!/bin/bash
set -e

# Create necessary directories
echo "🚀 Setting up Payslip Manager..."

# Create data directory if it doesn't exist
DATA_DIR="./data"
if [ ! -d "$DATA_DIR" ]; then
    echo "📂 Creating data directory..."
    mkdir -p "$DATA_DIR"
    chmod 755 "$DATA_DIR"
fi

# Create uploads directory
UPLOADS_DIR="./uploads"
if [ ! -d "$UPLOADS_DIR" ]; then
    echo "📁 Creating uploads directory..."
    mkdir -p "$UPLOADS_DIR"
    chmod 755 "$UPLOADS_DIR"
fi

# Create logs directory
LOGS_DIR="./logs"
if [ ! -d "$LOGS_DIR" ]; then
    echo "📝 Creating logs directory..."
    mkdir -p "$LOGS_DIR"
    chmod 755 "$LOGS_DIR"
fi

# Create .streamlit directory if it doesn't exist
STREAMLIT_DIR=".streamlit"
if [ ! -d "$STREAMLIT_DIR" ]; then
    echo "🔧 Creating .streamlit directory..."
    mkdir -p "$STREAMLIT_DIR"
    chmod 700 "$STREAMLIT_DIR"
    
    # Create default config files
    if [ ! -f "$STREAMLIT_DIR/config.toml" ]; then
        echo "⚙️  Creating default Streamlit config..."
        cp ".streamlit/config.toml.example" "$STREAMLIT_DIR/config.toml"
    fi
    
    if [ ! -f "$STREAMLIT_DIR/secrets.toml" ]; then
        echo "🔑 Creating default secrets file..."
        cp ".streamlit/secrets.template.toml" "$STREAMLIT_DIR/secrets.toml"
        echo "⚠️  Please update .streamlit/secrets.toml with your configuration"
    fi
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install package in development mode
echo "🔧 Installing package in development mode..."
pip install -e .

# Initialize the database
echo "💾 Initializing database..."
python -c "from src.database import init_db; init_db()"

echo "✅ Setup complete!"
echo "To start the application, run: streamlit run main.py"

exit 0
