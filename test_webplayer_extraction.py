#!/usr/bin/env python3
"""
Test script to trace step 3: extracting stream URL from webplayer.php
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test with the manual link mentioned earlier
WEBPLAYER_URL = "https://cdn.livetv869.me/webplayer.php?t=ifr&c=2874403&lang=en&eid=314788282&lid=2874403&ci=142&si=27"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://livetv.sx/'
}

def normalize_url(url, base_url):
    """Normalize a URL, handling protocol-relative URLs"""
    if url.startswith('//'):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}:{url}"
    elif url.startswith('/'):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    elif not url.startswith('http'):
        return urljoin(base_url, url)
    return url

print("="*80)
print("STEP 3: EXTRACTING STREAM URL FROM WEBPLAYER.PHP")
print("="*80)
print(f"\n📄 Fetching webplayer page: {WEBPLAYER_URL}\n")

try:
    response = requests.get(WEBPLAYER_URL, headers=HEADERS, timeout=15, verify=False)
    response.raise_for_status()
    print(f"✓ Status: {response.status_code}")
    print(f"✓ Content length: {len(response.text)} bytes\n")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("="*80)
    print("ANALYZING WEBPLAYER PAGE CONTENT")
    print("="*80)
    print()
    
    # 1. Check for direct iframe sources
    print("1️⃣ Checking for iframes...")
    iframes = soup.find_all('iframe', src=True)
    print(f"   Found {len(iframes)} iframe(s)")
    iframe_urls = []
    for iframe in iframes:
        src = iframe.get('src', '')
        full_url = normalize_url(src, WEBPLAYER_URL)
        iframe_urls.append(full_url)
        print(f"   - {full_url}")
    print()
    
    # 2. Check for script tags with stream URLs
    print("2️⃣ Checking for JavaScript variables with stream URLs...")
    scripts = soup.find_all('script')
    print(f"   Found {len(scripts)} script tag(s)")
    
    stream_patterns = [
        r'["\']([^"\']*\.m3u8[^"\']*)["\']',
        r'["\']([^"\']*\.mp4[^"\']*)["\']',
        r'["\']([^"\']*\.ts[^"\']*)["\']',
        r'hls\.src\s*=\s*["\']([^"\']+)["\']',
        r'player\.src\s*=\s*["\']([^"\']+)["\']',
        r'loadSource\(["\']([^"\']+)["\']',
        r'load\(["\']([^"\']+)["\']',
        r'play\(["\']([^"\']+)["\']',
    ]
    
    found_streams = []
    for script in scripts:
        script_text = script.string if script.string else ''
        for pattern in stream_patterns:
            matches = re.findall(pattern, script_text, re.IGNORECASE)
            for match in matches:
                if match and ('.m3u8' in match or '.mp4' in match or '.ts' in match):
                    full_url = normalize_url(match, WEBPLAYER_URL)
                    if full_url not in found_streams:
                        found_streams.append(full_url)
                        print(f"   ✓ Found stream: {full_url}")
    
    if not found_streams:
        print("   ✗ No stream URLs found in JavaScript")
    print()
    
    # 3. Check for data attributes
    print("3️⃣ Checking for data attributes...")
    data_attrs = ['data-src', 'data-url', 'data-stream', 'data-hls', 'data-source']
    data_streams = []
    for attr in data_attrs:
        elements = soup.find_all(attrs={attr: True})
        for elem in elements:
            value = elem.get(attr, '')
            if value and ('.m3u8' in value or '.mp4' in value or '.ts' in value):
                full_url = normalize_url(value, WEBPLAYER_URL)
                if full_url not in data_streams:
                    data_streams.append(full_url)
                    print(f"   ✓ Found in {attr}: {full_url}")
    
    if not data_streams:
        print("   ✗ No stream URLs found in data attributes")
    print()
    
    # 4. Check for API endpoints
    print("4️⃣ Checking for API endpoint patterns...")
    api_patterns = [
        r'["\']([^"\']*\/api\/stream[^"\']*)["\']',
        r'["\']([^"\']*\/api\/getstream[^"\']*)["\']',
        r'["\']([^"\']*\/getstream\.php[^"\']*)["\']',
    ]
    
    api_endpoints = []
    for script in scripts:
        script_text = script.string if script.string else ''
        for pattern in api_patterns:
            matches = re.findall(pattern, script_text, re.IGNORECASE)
            for match in matches:
                full_url = normalize_url(match, WEBPLAYER_URL)
                if full_url not in api_endpoints:
                    api_endpoints.append(full_url)
                    print(f"   ✓ Found API endpoint: {full_url}")
    
    if not api_endpoints:
        print("   ✗ No API endpoints found")
    print()
    
    # 5. Check for base64 encoded data URIs
    print("5️⃣ Checking for base64 encoded data...")
    base64_pattern = r'data:video/[^;]+;base64,'
    base64_found = False
    for script in scripts:
        script_text = script.string if script.string else ''
        if re.search(base64_pattern, script_text, re.IGNORECASE):
            base64_found = True
            print("   ✓ Found base64 encoded video data")
            break
    
    if not base64_found:
        print("   ✗ No base64 encoded data found")
    print()
    
    # 6. Check raw HTML for stream URLs
    print("6️⃣ Checking raw HTML for stream URLs...")
    html_streams = []
    html_patterns = [
        r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
        r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*',
    ]
    
    for pattern in html_patterns:
        matches = re.findall(pattern, response.text, re.IGNORECASE)
        for match in matches:
            if match not in html_streams:
                html_streams.append(match)
                print(f"   ✓ Found in HTML: {match}")
    
    if not html_streams:
        print("   ✗ No stream URLs found in raw HTML")
    print()
    
    # 7. Check for nested iframes (follow all valid iframes)
    all_stream_urls = list(set(found_streams + data_streams + html_streams))
    
    # Filter out broken PHP URLs
    valid_iframes = [url for url in iframe_urls if '<?php' not in url and url.startswith('http')]
    
    if valid_iframes and not all_stream_urls:
        print(f"7️⃣ Following {len(valid_iframes)} valid iframe(s) to find nested stream...")
        for idx, iframe_url in enumerate(valid_iframes, 1):
            print(f"   [{idx}/{len(valid_iframes)}] Following: {iframe_url}\n")
        
            try:
                iframe_response = requests.get(iframe_url, headers=HEADERS, timeout=15, verify=False)
                iframe_response.raise_for_status()
                print(f"      ✓ Iframe status: {iframe_response.status_code}")
                print(f"      ✓ Content length: {len(iframe_response.text)} bytes")
                
                # Check iframe content for streams
                iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                iframe_scripts = iframe_soup.find_all('script')
                
                # Check scripts in iframe
                for script in iframe_scripts:
                    script_text = script.string if script.string else ''
                    for pattern in stream_patterns:
                        matches = re.findall(pattern, script_text, re.IGNORECASE)
                        for match in matches:
                            if match and ('.m3u8' in match or '.mp4' in match):
                                full_url = normalize_url(match, iframe_url)
                                if full_url not in all_stream_urls:
                                    all_stream_urls.append(full_url)
                                    print(f"      ✓ Found stream in iframe script: {full_url}")
                
                # Check raw HTML in iframe
                for pattern in html_patterns:
                    matches = re.findall(pattern, iframe_response.text, re.IGNORECASE)
                    for match in matches:
                        if match not in all_stream_urls:
                            all_stream_urls.append(match)
                            print(f"      ✓ Found stream in iframe HTML: {match}")
                
                # Check for nested iframes in this iframe and follow them
                nested_iframes = iframe_soup.find_all('iframe', src=True)
                if nested_iframes:
                    print(f"      → Found {len(nested_iframes)} nested iframe(s) in this iframe")
                    for nested_idx, nested_iframe in enumerate(nested_iframes, 1):
                        nested_src = nested_iframe.get('src', '')
                        nested_full_url = normalize_url(nested_src, iframe_url)
                        print(f"         [{nested_idx}] Following nested iframe: {nested_full_url}")
                        
                        # Follow nested iframe
                        try:
                            nested_response = requests.get(nested_full_url, headers=HEADERS, timeout=15, verify=False)
                            nested_response.raise_for_status()
                            print(f"            ✓ Status: {nested_response.status_code}")
                            print(f"            ✓ Content length: {len(nested_response.text)} bytes")
                            
                            nested_soup = BeautifulSoup(nested_response.text, 'html.parser')
                            nested_scripts = nested_soup.find_all('script')
                            
                            # Check scripts in nested iframe
                            for script in nested_scripts:
                                script_text = script.string if script.string else ''
                                for pattern in stream_patterns:
                                    matches = re.findall(pattern, script_text, re.IGNORECASE)
                                    for match in matches:
                                        if match and ('.m3u8' in match or '.mp4' in match):
                                            full_url = normalize_url(match, nested_full_url)
                                            if full_url not in all_stream_urls:
                                                all_stream_urls.append(full_url)
                                                print(f"            ✓ Found stream: {full_url}")
                            
                            # Check raw HTML in nested iframe
                            for pattern in html_patterns:
                                matches = re.findall(pattern, nested_response.text, re.IGNORECASE)
                                for match in matches:
                                    if match not in all_stream_urls:
                                        all_stream_urls.append(match)
                                        print(f"            ✓ Found stream in HTML: {match}")
                            
                            # Check for even deeper nesting
                            deeper_iframes = nested_soup.find_all('iframe', src=True)
                            if deeper_iframes:
                                print(f"            → Found {len(deeper_iframes)} deeper nested iframe(s)")
                                for deeper_iframe in deeper_iframes:
                                    deeper_src = deeper_iframe.get('src', '')
                                    deeper_full_url = normalize_url(deeper_src, nested_full_url)
                                    print(f"               - {deeper_full_url}")
                        except Exception as e:
                            print(f"            ✗ Error: {e}")
                
            except Exception as e:
                print(f"      ✗ Error following iframe: {e}")
            print()
    
    # Summary
    print("="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print()
    
    if all_stream_urls:
        print(f"✓ SUCCESS: Found {len(all_stream_urls)} stream URL(s):\n")
        for i, stream_url in enumerate(all_stream_urls, 1):
            print(f"  {i}. {stream_url}")
    else:
        print("✗ NO STREAM URLS FOUND")
        print()
        print("This page likely loads the stream URL dynamically via JavaScript.")
        print("Next step: Use Playwright to execute JavaScript and intercept network requests.")
    
    print()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

