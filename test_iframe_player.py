#!/usr/bin/env python3
"""Test extracting stream from webplayer.iframe.php"""

import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not available. Install with: pip install playwright && playwright install")

iframe_url = "https://cdn.livetv872.me/export/webplayer.iframe.php?t=alieztv&c=245753&eid=332240467&lid=2914683&lang=en&m&dmn="

print("="*60)
print("Testing webplayer.iframe.php Extraction")
print("="*60)
print(f"\nURL: {iframe_url}\n")

def extract_from_iframe_html(url):
    """Extract stream from iframe player HTML"""
    headers = HEADERS.copy()
    headers['Referer'] = 'https://livetv872.me/'
    
    try:
        print("Fetching iframe player page...")
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            print(f"Content Length: {len(content)} bytes")
            print(f"\nFirst 2000 characters:")
            print("-"*60)
            print(content[:2000])
            print("-"*60)
            
            # Look for APL385 player embeds
            apl385_patterns = [
                r'(?:https?:)?//emb\.apl385\.me/[^\s"\'<>]+',
                r'emb\.apl385\.me/player/[^\s"\'<>]+',
                r'src=["\']([^"\']*emb\.apl385\.me[^"\']*)["\']',
                r'iframe[^>]+src=["\']([^"\']*apl385[^"\']*)["\']',
            ]
            
            print(f"\nLooking for APL385 player embeds...")
            for pattern in apl385_patterns:
                matches = re.findall(pattern, content, re.I)
                if matches:
                    print(f"  ✓ Found APL385 embed with pattern: {pattern[:50]}...")
                    for match in matches[:3]:
                        if isinstance(match, tuple):
                            match = match[0] if match else ""
                        if match:
                            if match.startswith('//'):
                                match = 'https:' + match
                            elif not match.startswith('http'):
                                match = 'https://' + match
                            print(f"    {match}")
                            return match
            
            # Look for .m3u8 URLs
            m3u8_pattern = r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
            m3u8_matches = re.findall(m3u8_pattern, content)
            print(f"\n.m3u8 URLs found: {len(m3u8_matches)}")
            for i, match in enumerate(m3u8_matches[:10], 1):
                if match.startswith('//'):
                    match = 'https:' + match
                print(f"  {i}. {match}")
                if i == 1:
                    return match
            
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
                        if match.startswith('//'):
                            match = 'https:' + match
                        elif not match.startswith('http'):
                            continue
                        print(f"  Found: {match[:150]}")
                        return match
            
            # Look for iframe src
            iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
            iframe_matches = re.findall(iframe_pattern, content, re.I)
            print(f"\nIframe src found: {len(iframe_matches)}")
            for i, iframe_src in enumerate(iframe_matches[:5], 1):
                print(f"  {i}. {iframe_src}")
                if 'apl385' in iframe_src.lower() or 'player' in iframe_src.lower():
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    elif not iframe_src.startswith('http'):
                        iframe_src = 'https://' + iframe_src
                    print(f"    → Recursively extracting from: {iframe_src}")
                    return extract_from_iframe_html(iframe_src)
            
            return None
        else:
            print(f"❌ Failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_with_playwright(url):
    """Extract stream using Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        print("⚠️  Playwright not available")
        return None
    
    print("\n" + "="*60)
    print("Trying Playwright extraction...")
    print("="*60)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS['User-Agent'],
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.set_extra_http_headers({'Referer': 'https://livetv872.me/'})
            
            stream_urls = []
            
            def handle_response(response):
                url = response.url
                if '.m3u8' in url:
                    if url not in stream_urls:
                        stream_urls.append(url)
                        print(f"    ✓ Found stream: {url}")
            
            page.on('response', handle_response)
            
            print(f"Loading: {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            print("Waiting for page to load...")
            page.wait_for_timeout(5000)
            
            # Check page content
            page_content = page.content()
            
            # Look for APL385 embeds
            apl385_pattern = r'(?:https?:)?//emb\.apl385\.me/[^\s"\'<>]+'
            apl385_matches = re.findall(apl385_pattern, page_content)
            if apl385_matches:
                print(f"\n  ✓ Found APL385 player in content")
                apl385_url = apl385_matches[0]
                if apl385_url.startswith('//'):
                    apl385_url = 'https:' + apl385_url
                print(f"    Loading APL385 player: {apl385_url}")
                
                # Navigate to APL385 player
                page.goto(apl385_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(10000)  # Wait for ad/redirect
            
            # Check for .m3u8 in content
            m3u8_pattern = r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
            content_matches = re.findall(m3u8_pattern, page_content)
            for match in content_matches:
                if match.startswith('//'):
                    match = 'https:' + match
                if match not in stream_urls:
                    stream_urls.append(match)
                    print(f"    ✓ Found in content: {match}")
            
            browser.close()
            
            if stream_urls:
                return stream_urls[0]
            else:
                print("  ⚠️  No stream URLs captured")
                return None
                
    except Exception as e:
        print(f"  ❌ Playwright error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Try HTML extraction first
stream_url = extract_from_iframe_html(iframe_url)

# If that fails, try Playwright
if not stream_url and PLAYWRIGHT_AVAILABLE:
    stream_url = extract_with_playwright(iframe_url)

# Results
print("\n" + "="*60)
print("Results")
print("="*60)
if stream_url:
    print(f"✓ Stream URL found: {stream_url}")
else:
    print("❌ No stream URL found")
