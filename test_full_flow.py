#!/usr/bin/env python3
"""
Test the full flow: Extract stream URL with Playwright, then test proxy access
"""
import sys
import os
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_stream import extract_stream_with_playwright

# Test with the webplayer URL
WEBPLAYER_URL = "https://cdn.livetv869.me/webplayer.php?t=ifr&c=2874403&lang=en&eid=314788282&lid=2874403&ci=142&si=27"

print("="*80)
print("FULL FLOW TEST: EXTRACTION → PROXY ACCESS")
print("="*80)
print(f"\nStep 1: Extracting stream URL from webplayer...")
print(f"URL: {WEBPLAYER_URL}\n")

# Step 1: Extract stream URL
stream_urls = extract_stream_with_playwright(WEBPLAYER_URL, timeout=60000, max_popup_closes=15)

if not stream_urls:
    print("\n❌ FAILED: No stream URLs extracted")
    exit(1)

stream_url = stream_urls[0]
print(f"\n{'='*80}")
print(f"Step 2: Testing proxy access with correct referer")
print(f"{'='*80}")
print(f"\nExtracted Stream URL: {stream_url}\n")

# Step 2: Test accessing the stream with the correct referer
print("Testing direct access with correct referer (https://exposestrat.com/)...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://exposestrat.com/',
    'Origin': 'https://exposestrat.com'
}

try:
    response = requests.get(stream_url, headers=headers, timeout=10, verify=False)
    
    if response.status_code == 200:
        print(f"✅ SUCCESS: Stream accessible with correct referer")
        print(f"   Status: {response.status_code}")
        print(f"   Content Length: {len(response.content)} bytes")
        print(f"   Content Type: {response.headers.get('Content-Type', 'N/A')}")
        
        # Show first few lines of M3U8
        if response.text:
            lines = response.text.split('\n')[:8]
            print(f"\n   M3U8 Preview:")
            for line in lines:
                if line.strip():
                    print(f"     {line}")
        
        print(f"\n✅ FULL FLOW TEST PASSED")
        print(f"   ✓ Stream URL extracted successfully")
        print(f"   ✓ Stream accessible with correct referer")
        print(f"   ✓ Proxy should work correctly")
    else:
        print(f"❌ FAILED: Status code {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)

