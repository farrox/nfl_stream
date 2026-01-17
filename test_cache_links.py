#!/usr/bin/env python3
"""Test fetching cache/links HTML directly"""

import requests
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://livetv872.me/enx/eventinfo/332240466_philadelphia_san_francisco/',
}

# Test URL from the iframe
cache_links_url = "https://cdn.livetv872.me/cache/links/en.332240466.html?17681717"

print("="*60)
print("Testing Cache/Links HTML Fetch")
print("="*60)
print(f"\nURL: {cache_links_url}\n")

try:
    print("Fetching cache/links HTML...")
    response = requests.get(cache_links_url, headers=HEADERS, timeout=10, verify=False)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        print(f"Content Length: {len(content)} bytes")
        print(f"\nFirst 1000 characters:")
        print("-"*60)
        print(content[:1000])
        print("-"*60)
        
        # Look for .m3u8 URLs
        m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
        m3u8_matches = re.findall(m3u8_pattern, content)
        print(f"\n.m3u8 URLs found: {len(m3u8_matches)}")
        for i, match in enumerate(m3u8_matches[:10], 1):
            print(f"  {i}. {match}")
        
        # Look for webplayer.php URLs
        webplayer_pattern = r'https?://[^\s"\'<>]+webplayer\.php[^\s"\'<>]*'
        webplayer_matches = re.findall(webplayer_pattern, content)
        print(f"\nwebplayer.php URLs found: {len(webplayer_matches)}")
        for i, match in enumerate(webplayer_matches[:10], 1):
            print(f"  {i}. {match}")
        
        # Look for onclick handlers
        onclick_pattern = r'onclick=["\']([^"\']+)["\']'
        onclick_matches = re.findall(onclick_pattern, content)
        print(f"\nonclick handlers found: {len(onclick_matches)}")
        for i, onclick in enumerate(onclick_matches[:5], 1):
            if '.m3u8' in onclick or 'webplayer' in onclick or 'stream' in onclick.lower():
                print(f"  {i}. {onclick[:200]}")
        
        # Look for href attributes with stream links
        href_pattern = r'href=["\']([^"\']+)["\']'
        href_matches = re.findall(href_pattern, content)
        stream_hrefs = [h for h in href_matches if '.m3u8' in h or 'webplayer' in h or 'stream' in h.lower()]
        print(f"\nStream-related hrefs found: {len(stream_hrefs)}")
        for i, href in enumerate(stream_hrefs[:10], 1):
            print(f"  {i}. {href}")
            
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
