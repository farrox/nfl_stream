#!/bin/bash

echo "================================================"
echo "🔍 Stream Server Diagnostics"
echo "================================================"
echo ""

# Check if server is running
if ps aux | grep -v grep | grep stream_refresher.py > /dev/null; then
    echo "✅ Server is RUNNING"
    PID=$(ps aux | grep -v grep | grep stream_refresher.py | awk '{print $2}')
    echo "   PID: $PID"
else
    echo "❌ Server is NOT running"
    echo "   Run: ./start.sh"
    exit 1
fi

echo ""

# Check if port is listening
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ Port 8080 is LISTENING"
else
    echo "❌ Port 8080 is NOT listening"
    exit 1
fi

echo ""

# Test API endpoint
echo "📡 Testing API..."
RESPONSE=$(curl -s http://localhost:8080/api/stream-info)
if [ $? -eq 0 ]; then
    echo "✅ API is responding"
    echo ""
    echo "Stream Information:"
    echo "$RESPONSE" | grep -o '"[^"]*":"[^"]*"' | while read line; do
        echo "   $line"
    done
else
    echo "❌ API is not responding"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ Everything is working!"
echo "================================================"
echo ""
echo "🌐 Open in browser:"
echo "   http://localhost:8080"
echo ""
echo "🎬 Or use with media player:"
echo "   vlc http://localhost:8080/stream.m3u8"
echo ""
echo "📄 Simple test page:"
echo "   open test_stream.html"
echo ""

