#!/bin/bash
# Clear all database, caches, and search results for a fresh start

echo "🧹 Clearing all data for fresh start..."
echo ""

# Remove database
if [ -f "streams.db" ]; then
    rm streams.db
    echo "✓ Removed streams.db"
else
    echo "  streams.db not found"
fi

# Remove last run date file
if [ -f ".last_run_date" ]; then
    rm .last_run_date
    echo "✓ Removed .last_run_date"
else
    echo "  .last_run_date not found"
fi

# Remove Python cache
if [ -d "__pycache__" ]; then
    rm -rf __pycache__
    echo "✓ Removed __pycache__"
else
    echo "  __pycache__ not found"
fi

# Remove any .pyc files
find . -name "*.pyc" -delete 2>/dev/null
echo "✓ Removed .pyc files"

echo ""
echo "✅ All cleared! Ready for fresh start."
echo ""
echo "Note: Browser localStorage (manual links) will need to be cleared manually:"
echo "  - Open browser DevTools (F12)"
echo "  - Go to Application > Local Storage > http://localhost:8080"
echo "  - Clear 'manualLinks' key"
echo ""

