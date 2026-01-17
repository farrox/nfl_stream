#!/bin/bash

echo "📱 Mobile Access Setup"
echo "====================="
echo ""

# Get local IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo "✅ Your server is running!"
echo ""
echo "📍 Local Access URL:"
echo "   http://$LOCAL_IP:8080"
echo ""
echo "📱 To access from your phone:"
echo "   1. Connect phone to SAME WiFi"
echo "   2. Open browser on phone"
echo "   3. Go to: http://$LOCAL_IP:8080"
echo ""

# Check if server is running
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ Server is RUNNING on port 8080"
else
    echo "❌ Server is NOT running!"
    echo "   Start it with: ./start.sh"
fi

echo ""
echo "🌐 Want access from anywhere?"
echo "   Option 1: Install ngrok: brew install ngrok"
echo "   Option 2: Read MOBILE_ACCESS.md for details"
echo ""

# Generate QR code if available
if command -v qrencode &> /dev/null; then
    echo "📱 QR Code (scan with phone camera):"
    echo ""
    echo "http://$LOCAL_IP:8080" | qrencode -t UTF8
    echo ""
else
    echo "💡 Install qrencode for QR code:"
    echo "   brew install qrencode"
    echo "   Then run: ./mobile_setup.sh"
fi

echo ""
echo "📖 Full guide: cat MOBILE_ACCESS.md"
echo ""

