#!/bin/bash
# Test script for live game detection

echo "=========================================="
echo "Testing Live Game Detection"
echo "=========================================="
echo ""

echo "Step 1: Starting the Flask server..."
echo "Run this in a separate terminal:"
echo "  cd /Users/ed/Developer/nfl_stream"
echo "  python3 stream_refresher.py"
echo ""
echo "Step 2: Once server is running, test the search API:"
echo "  curl 'http://localhost:8080/api/search?q=nfl' | python3 -m json.tool"
echo ""
echo "Step 3: Or open in browser:"
echo "  http://localhost:8080"
echo ""
echo "Step 4: Run the Python test script:"
echo "  python3 test_live_games.py"
echo ""
