#!/bin/bash

echo "🌐 ngrok Setup for Remote Access"
echo "=================================="
echo ""

# Check if ngrok is installed
if [ -f "./ngrok" ]; then
    echo "✅ ngrok is installed"
else
    echo "❌ ngrok not found"
    echo "Run this script again after download completes"
    exit 1
fi

echo ""
echo "📝 To use ngrok, you need a free account:"
echo ""
echo "1. Go to: https://dashboard.ngrok.com/signup"
echo "2. Sign up (free - takes 30 seconds)"
echo "3. Copy your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
read -p "Paste your authtoken here (or press Enter to skip): " authtoken

if [ ! -z "$authtoken" ]; then
    echo ""
    echo "⚙️ Setting up authtoken..."
    ./ngrok config add-authtoken "$authtoken"
    echo "✅ Authtoken saved!"
    echo ""
    echo "🚀 Starting ngrok tunnel..."
    echo ""
    ./ngrok http 8080
else
    echo ""
    echo "⏩ Skipped. To setup later, run:"
    echo "   ./ngrok config add-authtoken YOUR_TOKEN"
    echo "   ./ngrok http 8080"
fi



