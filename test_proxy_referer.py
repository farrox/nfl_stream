#!/usr/bin/env python3
"""
Test script to verify the proxy works with correct referer headers
"""
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test URL from our extraction
TEST_STREAM_URL = "https://d15.epicquesthero.com:999/hls/mtampabaybuccaneers.m3u8?md5=41cHnWLJ3zCl8Yee4ZDeuA&expires=1762721841"

# Referers to test (in order of priority)
REFERERS_TO_TRY = [
    'https://exposestrat.com/',
    'https://arizonaplay.club/',
    'https://livetv.sx/',
    'https://cdn.livetv869.me/'
]

print("="*80)
print("TESTING STREAM URL WITH DIFFERENT REFERER HEADERS")
print("="*80)
print(f"\n📄 Testing URL: {TEST_STREAM_URL}\n")
print("This will test which referer header allows access to the stream.\n")
print("="*80 + "\n")

headers_base = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

successful_referer = None
results = []

for referer in REFERERS_TO_TRY:
    print(f"Testing with Referer: {referer}")
    
    headers = headers_base.copy()
    headers['Referer'] = referer
    headers['Origin'] = referer.rstrip('/')
    
    try:
        response = requests.get(TEST_STREAM_URL, headers=headers, timeout=10, verify=False, allow_redirects=False)
        
        status = response.status_code
        status_text = "✅ SUCCESS" if status == 200 else f"❌ {status}"
        
        result = {
            'referer': referer,
            'status': status,
            'success': status == 200,
            'content_length': len(response.content) if response.content else 0,
            'content_preview': response.text[:200] if response.text else None
        }
        results.append(result)
        
        print(f"  Status: {status_text}")
        if status == 200:
            print(f"  Content Length: {len(response.content)} bytes")
            if response.text:
                # Show first few lines of M3U8
                lines = response.text.split('\n')[:5]
                print(f"  Content Preview:")
                for line in lines:
                    if line.strip():
                        print(f"    {line[:80]}")
            successful_referer = referer
            print(f"  ✅ This referer works!")
        elif status == 403:
            print(f"  ❌ 403 Forbidden - This referer is blocked")
        elif status == 404:
            print(f"  ❌ 404 Not Found - Stream URL may have expired")
        else:
            print(f"  ⚠ Unexpected status code")
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: {e}")
        results.append({
            'referer': referer,
            'status': None,
            'success': False,
            'error': str(e)
        })
    
    print()

print("="*80)
print("SUMMARY")
print("="*80)

if successful_referer:
    print(f"\n✅ SUCCESS: Found working referer!")
    print(f"   Referer: {successful_referer}")
    print(f"\n✅ The proxy should work with this referer.")
else:
    print(f"\n❌ NO WORKING REFERER FOUND")
    print(f"\nPossible reasons:")
    print(f"  - Stream URL may have expired (check expires parameter)")
    print(f"  - All referers are blocked")
    print(f"  - Additional headers/cookies may be required")
    print(f"\n⚠ Note: The stream URL includes an expires parameter.")
    print(f"   If it's expired, you'll need to extract a fresh URL.")

print("\n" + "="*80)
print("DETAILED RESULTS")
print("="*80)
for i, result in enumerate(results, 1):
    print(f"\n{i}. Referer: {result['referer']}")
    if result.get('error'):
        print(f"   Error: {result['error']}")
    else:
        print(f"   Status: {result['status']}")
        print(f"   Success: {'Yes' if result['success'] else 'No'}")
        if result['success']:
            print(f"   Content Length: {result['content_length']} bytes")

print("\n" + "="*80)

