#!/bin/bash
# Klar Search Engine - Linux/Mac Startup Script
# Run: ./start.sh

set -e

echo ""
echo "================================================================"
echo "         KLAR SEARCH ENGINE - Starting Server"
echo "================================================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ first"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import flask" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Check if index exists
if [ ! -f "data/index/search_index.pkl" ]; then
    echo ""
    echo "================================================================"
    echo "WARNING: Search index not found!"
    echo "================================================================"
    echo ""
    echo "You must run initialization first:"
    echo "   python init_kse.py"
    echo ""
    echo "This will take 2-4 hours but only needs to be done once."
    echo ""
    read -p "Do you want to initialize now? (y/n): " continue
    if [[ $continue == "y" || $continue == "Y" ]]; then
        python init_kse.py
    else
        echo ""
        echo "Exiting. Please run init_kse.py first."
        exit 1
    fi
fi

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

# Start the server
echo ""
echo "Starting Klar Search Engine Server..."
echo ""
echo "Server will be available at:"
echo "  - Local:  http://localhost:5000"
echo "  - Network: http://$LOCAL_IP:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python start_server.py
