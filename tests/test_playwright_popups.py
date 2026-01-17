#!/usr/bin/env python3
"""
Test script to test Playwright extraction with multiple popup handling
"""
import sys
import os

# Add the parent directory to the path so we can import extract_stream
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extract_stream import extract_stream_with_playwright

# Test with the webplayer URL we've been testing
TEST_URL = "https://cdn.livetv869.me/webplayer.php?t=ifr&c=2874403&lang=en&eid=314788282&lid=2874403&ci=142&si=27"

print("="*80)
print("TESTING PLAYWRIGHT EXTRACTION WITH MULTIPLE POPUP HANDLING")
print("="*80)
print(f"\n📄 Testing URL: {TEST_URL}\n")
print("This will:")
print("  1. Navigate to the webplayer page")
print("  2. Hide the popup overlay (#localpp)")
print("  3. Close all popup windows (up to 15 times)")
print("  4. Extract stream URLs from network responses and page content")
print("\n" + "="*80 + "\n")

# Run the extraction
stream_urls = extract_stream_with_playwright(TEST_URL, timeout=60000, max_popup_closes=15)

# Display results
print("\n" + "="*80)
print("TEST RESULTS")
print("="*80)

if stream_urls:
    print(f"\n✅ SUCCESS: Found {len(stream_urls)} stream URL(s):\n")
    for i, stream_url in enumerate(stream_urls, 1):
        print(f"  {i}. {stream_url}")
    print()
else:
    print("\n❌ NO STREAM URLS FOUND")
    print("\nPossible reasons:")
    print("  - Popups weren't fully closed")
    print("  - Stream URL is loaded via JavaScript that needs more time")
    print("  - Stream URL is in a different format (not .m3u8)")
    print("  - Network interception didn't capture the stream request")
    print()

print("="*80)
