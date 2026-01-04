#!/bin/bash

echo "============================================"
echo "🎥 Auto-Refreshing Stream Player"
echo "============================================"
echo ""
echo "Starting server..."
echo ""

cd /Users/ed/Developer/nfl_stream

# Kill all processes on port 8080
echo "🔪 Killing all processes on port 8080..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 1

# Verify port is free
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "⚠️  Warning: Port 8080 may still be in use"
else
    echo "✅ Port 8080 is free"
fi
echo ""

# Check if dependencies are installed
if ! python -c "import flask, requests" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q flask requests
    echo "✓ Dependencies installed"
    echo ""
fi

echo "🚀 Starting stream server..."
echo "📺 Open in browser: http://localhost:8080"
echo "⌨️  Press Ctrl+C to stop"
echo ""
echo "============================================"
echo ""

python stream_refresher.py

