#!/usr/bin/env python3
"""Test extracting stream from APL385 player"""

import requests
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://cdn.livetv872.me/webplayer2.php',
}

player_url = "https://emb.apl385.me/player/live.php?id=245753&w=728&h=480"

print("="*60)
print("Testing APL385 Player Extraction")
print("="*60)
print(f"\nURL: {player_url}\n")

try:
    print("Fetching player page...")
    response = requests.get(player_url, headers=HEADERS, timeout=10, verify=False)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        print(f"Content Length: {len(content)} bytes")
        print(f"\nFirst 2000 characters:")
        print("-"*60)
        print(content[:2000])
        print("-"*60)
        
        # Look for .m3u8 URLs
        m3u8_pattern = r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
        m3u8_matches = re.findall(m3u8_pattern, content)
        print(f"\n.m3u8 URLs found: {len(m3u8_matches)}")
        for i, match in enumerate(m3u8_matches[:10], 1):
            if match.startswith('//'):
                match = 'https:' + match
            print(f"  {i}. {match}")
        
        # Look for JavaScript variables
        js_patterns = [
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'src\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'url\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'stream\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]
        
        print(f"\nJavaScript patterns:")
        for pattern in js_patterns:
            matches = re.findall(pattern, content, re.I)
            for match in matches:
                if '.m3u8' in match:
                    print(f"  Found: {match[:150]}")
        
        # Look for iframe src
        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
        iframe_matches = re.findall(iframe_pattern, content, re.I)
        print(f"\nIframe src found: {len(iframe_matches)}")
        for i, iframe_src in enumerate(iframe_matches[:5], 1):
            print(f"  {i}. {iframe_src}")
            
    else:
        print(f"❌ Failed with status {response.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
