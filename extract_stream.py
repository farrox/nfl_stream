
#!/usr/bin/env python3
"""
Script to extract stream URL from liveTv.sx and other streaming sites
"""
import re
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse

# Try to import Playwright for JavaScript-based extraction
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

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

def extract_livetv_events(allupcoming_url, max_events=5):
    """Extract event links from liveTv.sx allupcoming page"""
    print(f"\n{'='*60}")
    print(f"STEP 1: Extracting events from {allupcoming_url}")
    print(f"{'='*60}\n")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(allupcoming_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links - they typically have pattern /enx/eventinfo/ID_name/
        event_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if '/enx/eventinfo/' in href:
                full_url = normalize_url(href, allupcoming_url)
                if full_url not in event_links:
                    event_links.append(full_url)
        
        print(f"Found {len(event_links)} event links")
        if event_links:
            print(f"\nFirst {min(max_events, len(event_links))} events:")
            for i, event_url in enumerate(event_links[:max_events], 1):
                print(f"  {i}. {event_url}")
        
        return event_links[:max_events] if max_events else event_links
        
    except requests.RequestException as e:
        print(f"Error fetching events: {e}")
        return []

def extract_livetv_player_links(event_url):
    """Extract player links from a liveTv.sx event page"""
    print(f"\n{'='*60}")
    print(f"STEP 2: Extracting player links from event page")
    print(f"{'='*60}\n")
    print(f"Event URL: {event_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(event_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for webplayer.php links
        player_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if 'webplayer.php' in href:
                full_url = normalize_url(href, event_url)
                if full_url not in player_links:
                    player_links.append(full_url)
        
        # Also check for webplayer.php in the HTML directly
        webplayer_pattern = r'//cdn\.livetv869\.me/webplayer\.php[^\s"\'\)]+'
        matches = re.findall(webplayer_pattern, response.text)
        for match in matches:
            full_url = normalize_url(match, event_url)
            if full_url not in player_links:
                player_links.append(full_url)
        
        print(f"Found {len(player_links)} player links")
        for i, player_url in enumerate(player_links, 1):
            print(f"  {i}. {player_url}")
        
        return player_links
        
    except requests.RequestException as e:
        print(f"Error fetching event page: {e}")
        return []

def extract_stream_from_player(player_url, max_depth=5):
    """Extract actual stream URL from a player page, following iframes"""
    print(f"\n{'='*60}")
    print(f"STEP 3: Extracting stream from player page")
    print(f"{'='*60}\n")
    print(f"Player URL: {player_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    stream_urls = []
    visited_urls = set()
    
    def fetch_and_extract(url, depth=0):
        if depth > max_depth or url in visited_urls:
            return []
        
        visited_urls.add(url)
        print(f"\n  [Depth {depth}] Fetching: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            print(f"  Status: {response.status_code}, Final URL: {response.url}")
            
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for .m3u8 URLs - be more strict to avoid false positives
            # Match URLs that start with http/https and end with .m3u8 (with optional query params)
            m3u8_pattern = r'https?://[^\s"\'\)<>\{\}]+\.m3u8(?:\?[^\s"\'\)<>]*)?'
            m3u8_urls = re.findall(m3u8_pattern, html_content)
            # Filter out URLs that look like JavaScript code (contain common JS patterns)
            valid_m3u8_urls = []
            for m3u8_url in m3u8_urls:
                # Skip if it contains JavaScript-like patterns
                if any(pattern in m3u8_url for pattern in ['const ', 'function', 'return ', 'Math.', 'Date.', 'toString']):
                    continue
                # Must be a reasonable length (not too long)
                if len(m3u8_url) > 500:
                    continue
                valid_m3u8_urls.append(m3u8_url)
            
            if valid_m3u8_urls:
                print(f"  ✓ Found {len(valid_m3u8_urls)} .m3u8 URLs")
                for m3u8_url in valid_m3u8_urls:
                    if m3u8_url not in stream_urls:
                        stream_urls.append(m3u8_url)
                        print(f"    → {m3u8_url}")
            
            # Look for video tags
            videos = soup.find_all('video')
            for video in videos:
                src = video.get('src', '')
                if src and ('.m3u8' in src or '.mp4' in src):
                    full_src = normalize_url(src, url)
                    if full_src not in stream_urls:
                        stream_urls.append(full_src)
                        print(f"  ✓ Found video src: {full_src}")
                
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src', '')
                    if src and ('.m3u8' in src or '.mp4' in src):
                        full_src = normalize_url(src, url)
                        if full_src not in stream_urls:
                            stream_urls.append(full_src)
                            print(f"  ✓ Found video source: {full_src}")
            
            # Look for iframes (but skip ad iframes)
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src and 'getbanner' not in src and 'ads' not in src.lower():
                    full_src = normalize_url(src, url)
                    if full_src not in visited_urls:
                        print(f"  → Following iframe: {full_src}")
                        fetch_and_extract(full_src, depth + 1)
            
            # Check for API endpoints that might return stream URLs
            # Common patterns: /api/stream, /api/getstream, /getstream.php
            if 'lotusgamehd' in url.lower() or 'antenasport' in url.lower():
                # Extract parameter from URL (e.g., hd=280)
                param_match = re.search(r'[?&](hd|id|stream|channel)=([^&]+)', url)
                if param_match:
                    param_name, param_value = param_match.groups()
                    base_url = url.split('/')[0] + '//' + url.split('/')[2]
                    api_endpoints = [
                        f"{base_url}/api/stream?{param_name}={param_value}",
                        f"{base_url}/api/getstream?{param_name}={param_value}",
                        f"{base_url}/getstream.php?{param_name}={param_value}",
                    ]
                    for api_url in api_endpoints:
                        if api_url not in visited_urls:
                            try:
                                api_response = requests.get(api_url, headers=headers, timeout=5)
                                if api_response.status_code == 200:
                                    api_m3u8 = re.findall(r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*', api_response.text)
                                    if api_m3u8:
                                        for m3u8_url in api_m3u8:
                                            if m3u8_url not in stream_urls:
                                                stream_urls.append(m3u8_url)
                                                print(f"  ✓ Found via API endpoint: {m3u8_url}")
                            except:
                                pass
            
            # Look for JavaScript variables with stream URLs - expanded patterns
            js_patterns = [
                r'(?:file|source|src|url|stream|hlsUrl|streamUrl|hls\.src|player\.src)\s*[:=]\s*["\'](https?://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
                r'["\'](https?://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
                r'(?:loadSource|load|play)\s*\(["\'](https?://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
                r'\.m3u8["\']?\s*[,\}]',  # Look for .m3u8 at end of strings
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.I)
                for match in matches:
                    # Validate it's a real URL and not JavaScript code
                    if (match.startswith('http') and 
                        '.m3u8' in match and 
                        len(match) < 500 and
                        not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ', 'Math.', 'Date.', 'toString', 'slice'])):
                        if match not in stream_urls:
                            stream_urls.append(match)
                            print(f"  ✓ Found in JS: {match}")
            
            # Look for base64 encoded URLs or data URIs
            base64_pattern = r'data:video/[^;]+;base64,[A-Za-z0-9+/=]+'
            base64_matches = re.findall(base64_pattern, html_content)
            if base64_matches:
                print(f"  → Found {len(base64_matches)} base64 data URIs (may contain stream info)")
            
            # Look for fetch/XHR patterns that might reveal API endpoints
            fetch_patterns = [
                r'fetch\s*\(["\']([^"\']+)["\']',
                r'\.get\s*\(["\']([^"\']+)["\']',
                r'\.post\s*\(["\']([^"\']+)["\']',
                r'XMLHttpRequest[^}]+open\s*\(["\']GET["\'],\s*["\']([^"\']+)["\']',
            ]
            for pattern in fetch_patterns:
                matches = re.findall(pattern, html_content, re.I)
                for match in matches:
                    if any(x in match.lower() for x in ['.m3u8', 'stream', 'playlist', 'hls', 'live']):
                        print(f"  → Found potential API endpoint: {match}")
            
            # Look for data attributes that might contain stream URLs
            data_attrs = soup.find_all(attrs={'data-src': True}) + soup.find_all(attrs={'data-url': True}) + soup.find_all(attrs={'data-stream': True})
            for elem in data_attrs:
                for attr in ['data-src', 'data-url', 'data-stream']:
                    val = elem.get(attr, '')
                    if val and ('.m3u8' in val or 'stream' in val.lower()):
                        full_val = normalize_url(val, url)
                        if full_val not in stream_urls and full_val.startswith('http'):
                            stream_urls.append(full_val)
                            print(f"  ✓ Found in data attribute ({attr}): {full_val}")
            
        except requests.RequestException as e:
            print(f"  ✗ Error: {e}")
            return []
        
        return stream_urls
    
    fetch_and_extract(player_url)
    
    # If no stream URLs found, check if the page uses JavaScript to load streams
    if not stream_urls:
        print(f"\n  ⚠ No direct stream URLs found in HTML")
        print(f"  → This page likely loads the stream URL dynamically via JavaScript")
        if PLAYWRIGHT_AVAILABLE:
            print(f"  → Attempting Playwright-based extraction...")
            playwright_streams = extract_stream_with_playwright(player_url)
            if playwright_streams:
                stream_urls.extend(playwright_streams)
        else:
            print(f"  → Install Playwright for JavaScript-based extraction: pip install playwright && playwright install")
            print(f"  → Or try using the webplayer.php URL directly as some players can handle it")
    
    return stream_urls

def extract_stream_with_playwright(player_url, timeout=30000, max_popup_closes=15):
    """Extract stream URL using Playwright to execute JavaScript and intercept network requests.
    Handles multiple popup windows that need to be closed repeatedly."""
    if not PLAYWRIGHT_AVAILABLE:
        print("  ✗ Playwright not available. Install with: pip install playwright && playwright install")
        return []
    
    print(f"\n  [Playwright] Launching browser to extract stream URL...")
    stream_urls = []
    
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            # Store stream URLs with their request info (headers, referer)
            stream_info = []
            
            # Intercept network requests to capture headers
            def handle_request(request):
                url = request.url
                if '.m3u8' in url.lower():
                    # Capture the request with its headers
                    headers = request.headers
                    referer = headers.get('referer', player_url)
                    info = {
                        'url': url,
                        'headers': dict(headers),
                        'referer': referer
                    }
                    if info not in stream_info:
                        stream_info.append(info)
                        print(f"  ✓ [Playwright] Captured .m3u8 request: {url}")
                        print(f"     Referer: {referer}")
            
            # Intercept network responses to capture .m3u8 URLs
            def handle_response(response):
                url = response.url
                if '.m3u8' in url.lower():
                    # Get the request that triggered this response
                    request = response.request
                    headers = request.headers
                    referer = headers.get('referer', player_url)
                    
                    info = {
                        'url': url,
                        'headers': dict(headers),
                        'referer': referer
                    }
                    
                    if info not in stream_info:
                        stream_info.append(info)
                        print(f"  ✓ [Playwright] Captured .m3u8 URL: {url}")
                        print(f"     Referer: {referer}")
                    
                    # Also add to simple list for backward compatibility
                    if url not in stream_urls:
                        stream_urls.append(url)
                
                # Also check response body for m3u8 URLs
                try:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'text' in content_type or 'json' in content_type:
                            body = response.text()
                            m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                            matches = re.findall(m3u8_pattern, body)
                            for match in matches:
                                if match not in stream_urls:
                                    stream_urls.append(match)
                                    print(f"  ✓ [Playwright] Found .m3u8 URL in response: {match}")
                except:
                    pass
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # Navigate to the page
            print(f"  [Playwright] Navigating to: {player_url}")
            try:
                page.goto(player_url, wait_until='domcontentloaded', timeout=timeout)
                
                # Wait for initial page load
                page.wait_for_timeout(2000)
                
                # Handle popup overlay div (localpp) - hide it if present
                try:
                    popup_overlay = page.query_selector('#localpp')
                    if popup_overlay:
                        print(f"  [Playwright] Found popup overlay, hiding it...")
                        # Hide the overlay by setting display to none
                        page.evaluate("""
                            const overlay = document.getElementById('localpp');
                            if (overlay) {
                                overlay.style.display = 'none';
                            }
                        """)
                        page.wait_for_timeout(500)
                except:
                    pass
                
                # Handle multiple popup windows - close them repeatedly
                popup_close_count = 0
                while popup_close_count < max_popup_closes:
                    # Get all pages (main page + popups)
                    all_pages = context.pages
                    
                    if len(all_pages) <= 1:
                        # No popups, break
                        break
                    
                    # Close all popup windows except the main page
                    closed_any = False
                    for popup_page in all_pages:
                        if popup_page != page:
                            try:
                                print(f"  [Playwright] Closing popup window {popup_close_count + 1}...")
                                popup_page.close()
                                closed_any = True
                                popup_close_count += 1
                            except:
                                pass
                    
                    if not closed_any:
                        break
                    
                    # Wait a bit before checking for more popups
                    page.wait_for_timeout(1000)
                    
                    # Check if popup overlay appeared again and hide it
                    try:
                        popup_overlay = page.query_selector('#localpp')
                        if popup_overlay:
                            page.evaluate("""
                                const overlay = document.getElementById('localpp');
                                if (overlay) {
                                    overlay.style.display = 'none';
                                }
                            """)
                    except:
                        pass
                
                if popup_close_count > 0:
                    print(f"  ✓ [Playwright] Closed {popup_close_count} popup window(s)")
                
                # Wait for any delayed JavaScript execution after popups are closed
                page.wait_for_timeout(3000)
                
                # Follow iframes to find streams in nested pages
                print(f"  [Playwright] Checking for iframes...")
                try:
                    iframes = page.query_selector_all('iframe')
                    for i, iframe in enumerate(iframes):
                        try:
                            iframe_src = iframe.get_attribute('src')
                            if iframe_src:
                                print(f"  [Playwright] Found iframe {i+1}: {iframe_src[:80]}...")
                                # Wait a bit for iframe to load
                                page.wait_for_timeout(2000)
                        except:
                            pass
                except:
                    pass
                
                # Check all pages (main + iframes) for stream URLs
                all_pages = context.pages
                for check_page in all_pages:
                    try:
                        page_content = check_page.content()
                        m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                        content_matches = re.findall(m3u8_pattern, page_content)
                        for match in content_matches:
                            if match not in stream_urls:
                                # Filter out false positives
                                if not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ', 'Math.', 'Date.']):
                                    stream_urls.append(match)
                                    print(f"  ✓ [Playwright] Found .m3u8 URL in page content: {match}")
                    except:
                        pass
                
                # Wait a bit more for any delayed stream requests
                page.wait_for_timeout(5000)
                
            except PlaywrightTimeoutError:
                print(f"  ⚠ [Playwright] Timeout waiting for page to load, but checking captured URLs...")
            
            browser.close()
            
    except Exception as e:
        print(f"  ✗ [Playwright] Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    if stream_urls:
        print(f"  ✓ [Playwright] Successfully extracted {len(stream_urls)} stream URL(s)")
        if stream_info:
            print(f"  → Captured {len(stream_info)} stream URL(s) with request headers")
            print(f"\n  📋 Stream URLs with headers:")
            for i, info in enumerate(stream_info, 1):
                print(f"     {i}. {info['url']}")
                print(f"        Referer: {info['referer']}")
                # Show important headers
                important_headers = ['user-agent', 'referer', 'origin', 'cookie']
                for header_name in important_headers:
                    if header_name in info['headers']:
                        header_value = info['headers'][header_name]
                        if len(header_value) > 100:
                            header_value = header_value[:100] + "..."
                        print(f"        {header_name}: {header_value}")
    else:
        print(f"  ✗ [Playwright] No stream URLs captured")
    
    # Return URLs with their referer info for proper access
    # Format: return list of dicts with url and referer, or just URLs for backward compatibility
    return stream_urls

def debug_livetv_sx(start_url="https://livetv.sx/enx/allupcoming/"):
    """Debug the entire liveTv.sx extraction process"""
    print("\n" + "="*60)
    print("DEBUGGING liveTv.sx EXTRACTION PROCESS")
    print("="*60)
    
    # Step 1: Get events
    events = extract_livetv_events(start_url, max_events=3)
    
    if not events:
        print("\n✗ No events found. Exiting.")
        return []
    
    all_streams = []
    
    # Step 2: For each event, get player links
    for event_url in events:
        print(f"\n{'='*60}")
        print(f"Processing event: {event_url}")
        print(f"{'='*60}")
        
        player_links = extract_livetv_player_links(event_url)
        
        if not player_links:
            print("  ✗ No player links found for this event")
            continue
        
        # Step 3: For each player, extract stream
        for player_url in player_links[:2]:  # Limit to first 2 players per event
            streams = extract_stream_from_player(player_url)
            all_streams.extend(streams)
            
            if streams:
                print(f"\n  ✓ Successfully extracted {len(streams)} stream(s) from this player")
                break  # Stop after first successful extraction
    
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    unique_streams = []
    for stream in all_streams:
        if stream not in unique_streams:
            unique_streams.append(stream)
    
    if unique_streams:
        print(f"\n✓ Found {len(unique_streams)} unique stream URL(s):\n")
        for i, stream in enumerate(unique_streams, 1):
            print(f"  {i}. {stream}")
    else:
        print("\n✗ No stream URLs found.")
    
    return unique_streams

def extract_stream_url(url):
    """Extract stream URL from the given webpage"""
    print(f"Fetching {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("\n" + "="*60)
        print("SEARCHING FOR STREAMS...")
        print("="*60 + "\n")
        
        # Look for common stream patterns
        stream_urls = []
        
        # Pattern 1: Look for .m3u8 URLs (HLS streams)
        m3u8_pattern = r'https?://[^\s"\'\)]+\.m3u8[^\s"\'\)]*'
        m3u8_urls = re.findall(m3u8_pattern, html_content)
        if m3u8_urls:
            print("Found .m3u8 streams (HLS):")
            for stream in m3u8_urls:
                print(f"  - {stream}")
                stream_urls.append(stream)
        
        # Pattern 2: Look for .mp4 URLs
        mp4_pattern = r'https?://[^\s"\'\)]+\.mp4[^\s"\'\)]*'
        mp4_urls = re.findall(mp4_pattern, html_content)
        if mp4_urls:
            print("\nFound .mp4 streams:")
            for stream in mp4_urls:
                print(f"  - {stream}")
                stream_urls.append(stream)
        
        # Pattern 3: Look for iframe sources
        iframes = soup.find_all('iframe')
        if iframes:
            print("\nFound iframes:")
            for iframe in iframes:
                src = iframe.get('src', '')
                if src:
                    print(f"  - {src}")
                    stream_urls.append(src)
        
        # Pattern 4: Look for video sources
        videos = soup.find_all('video')
        if videos:
            print("\nFound video tags:")
            for video in videos:
                src = video.get('src', '')
                if src:
                    print(f"  - {src}")
                    stream_urls.append(src)
                # Check source tags within video
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src', '')
                    if src:
                        print(f"  - {src}")
                        stream_urls.append(src)
        
        # Pattern 5: Look for common streaming patterns in JavaScript
        js_patterns = [
            r'source["\']?\s*:\s*["\']([^"\']+)["\']',
            r'file["\']?\s*:\s*["\']([^"\']+)["\']',
            r'src["\']?\s*:\s*["\']([^"\']+)["\']',
            r'url["\']?\s*:\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if any(ext in match for ext in ['.m3u8', '.mp4', '.ts', 'stream']):
                    if match not in stream_urls:
                        stream_urls.append(match)
        
        # Pattern 6: Look for script tags with JSON data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Try to find JSON objects with stream data
                try:
                    json_matches = re.findall(r'\{[^{}]*(?:"(?:file|source|src|url)"\s*:\s*"[^"]+")[^{}]*\}', script.string)
                    for json_str in json_matches:
                        try:
                            data = json.loads(json_str)
                            for key in ['file', 'source', 'src', 'url']:
                                if key in data and data[key]:
                                    print(f"\nFound in JSON ({key}):")
                                    print(f"  - {data[key]}")
                                    stream_urls.append(data[key])
                        except:
                            pass
                except:
                    pass
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        if stream_urls:
            # Remove duplicates while preserving order
            unique_streams = []
            for url in stream_urls:
                if url not in unique_streams:
                    unique_streams.append(url)
            
            print(f"\nFound {len(unique_streams)} unique stream URL(s):\n")
            for i, stream in enumerate(unique_streams, 1):
                print(f"{i}. {stream}")
            
            return unique_streams
        else:
            print("\nNo stream URLs found.")
            print("\nPage title:", soup.title.string if soup.title else "N/A")
            print("\nYou may need to:")
            print("  1. Check the page in a browser with Developer Tools")
            print("  2. Look at the Network tab while the stream loads")
            print("  3. The stream might be loaded dynamically with JavaScript")
            return []
            
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []

if __name__ == "__main__":
    import sys
    
    # Check if URL is provided as argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://livetv.sx/enx/allupcoming/"
    
    # Check if it's a webplayer.php URL
    if 'webplayer.php' in url:
        print("Detected webplayer.php URL - extracting stream...")
        streams = extract_stream_from_player(url)
    # Check if it's a liveTv.sx allupcoming page
    elif 'livetv.sx' in url and 'allupcoming' in url:
        print("Detected liveTv.sx allupcoming page - using debug mode")
        streams = debug_livetv_sx(url)
    else:
        streams = extract_stream_url(url)
    
    if streams:
        print("\n" + "="*60)
        print("To play the stream, you can use:")
        print("="*60)
        print(f"\nVLC: vlc '{streams[0]}'")
        print(f"ffplay: ffplay '{streams[0]}'")
        print(f"mpv: mpv '{streams[0]}'")

