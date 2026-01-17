#!/bin/bash
cd /Users/ed/Developer/nfl_stream
echo "Running test_hash_fragment.py..."
python3 test_hash_fragment.py
echo ""
echo "Running extract_hash_stream.py..."
python3 extract_hash_stream.py
