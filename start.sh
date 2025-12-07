#!/bin/bash

# Mathematical Question Refinement Chatbot - Startup Script
# This script installs dependencies and starts the FastAPI server

echo "🚀 Mathematical Question Refinement Chatbot Setup"
echo "=================================================="
echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install fastapi uvicorn langchain langchain-openai openai faiss-cpu sentence-transformers pydantic python-multipart numpy --break-system-packages

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    echo "Please run manually: pip install -r requirements.txt --break-system-packages"
    exit 1
fi

echo ""
echo "✅ Dependencies installed successfully"
echo ""

# Start the server
echo "🌐 Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
