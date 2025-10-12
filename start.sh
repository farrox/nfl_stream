#!/bin/bash

echo "============================================"
echo "🎥 Auto-Refreshing Stream Player"
echo "============================================"
echo ""
echo "Starting server..."
echo ""

cd /Users/ed/Developer/streams

# Check if dependencies are installed
if ! python -c "import flask, requests" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q flask requests
    echo "✓ Dependencies installed"
    echo ""
fi

echo "🚀 Starting stream server..."
echo "📺 Open in browser: http://localhost:5000"
echo "⌨️  Press Ctrl+C to stop"
echo ""
echo "============================================"
echo ""

python stream_refresher.py

