#!/usr/bin/env python3
"""
Extract actual stream URL from LiveTV872.me hash fragment URL
Specifically for: https://livetv872.me/enx/eventinfo/332240466_philadelphia_san_francisco/#webplayer_alieztv|245753|332240466|2914683|142|27|en
"""

import re
import requests
import urllib.parse
import urllib3
import sys

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not available. Install with: pip install playwright && playwright install")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def parse_hash_fragment(url):
    """Parse webplayer hash fragment from URL"""
    if '#' not in url:
        return None
    
    hash_part = url.split('#', 1)[1]
    if not hash_part.startswith('webplayer_'):
        return None
    
    parts = hash_part.replace('webplayer_', '').split('|')
    if len(parts) < 7:
        return None
    
    return {
        'provider': parts[0],
        'channel_id': parts[1],
        'event_id': parts[2],
        'lid': parts[3],
        'ci': parts[4],
        'si': parts[5],
        'lang': parts[6]
    }

def construct_webplayer_url(params, cdn_domain='https://cdn.livetv872.me', use_webplayer2=False, use_iframe=False):
    """Construct webplayer URL from parameters"""
    if use_iframe:
        # webplayer.iframe.php format
        return (
            f"{cdn_domain}/export/webplayer.iframe.php?"
            f"t={params.get('provider', 'alieztv')}&"
            f"c={params['channel_id']}&"
            f"eid={params['event_id']}&"
            f"lid={params['lid']}&"
            f"lang={params['lang']}&"
            f"m&dmn="
        )
    
    webplayer_file = 'webplayer2.php' if use_webplayer2 else 'webplayer.php'
    t_param = params.get('provider', 'ifr') if use_webplayer2 else 'ifr'
    
    return (
        f"{cdn_domain}/{webplayer_file}?"
        f"t={t_param}&"
        f"c={params['channel_id']}&"
        f"lang={params['lang']}&"
        f"eid={params['event_id']}&"
        f"lid={params['lid']}&"
        f"ci={params['ci']}&"
        f"si={params['si']}"
    )

def extract_stream_with_playwright(webplayer_url, referer_url, timeout=30000):
    """Extract stream URL using Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        return None
    
    print(f"\n[Playwright] Extracting stream from: {webplayer_url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS['User-Agent'],
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # Set referer
            page.set_extra_http_headers({'Referer': referer_url})
            
            # Prepare headers for direct requests
            headers = HEADERS.copy()
            headers['Referer'] = referer_url
            
            # Listen for network requests to capture .m3u8 URLs
            stream_urls = []
            
            def handle_response(response):
                url = response.url
                if '.m3u8' in url:
                    if url not in stream_urls:
                        stream_urls.append(url)
                        print(f"  ✓ Found stream: {url}")
            
            page.on('response', handle_response)
            
            # Navigate to webplayer
            print(f"  Loading webplayer page...")
            page.goto(webplayer_url, wait_until='domcontentloaded', timeout=timeout)
            
            # Wait a bit for JavaScript to load streams
            print(f"  Waiting for stream to load...")
            page.wait_for_timeout(5000)
            
            # Check for iframes - especially cache/links iframes
            iframes = page.query_selector_all('iframe')
            print(f"  Found {len(iframes)} iframe(s)")
            
            for iframe in iframes:
                try:
                    iframe_src = iframe.get_attribute('src')
                    if iframe_src:
                        print(f"  Checking iframe: {iframe_src}")
                        
                        # Make URL absolute if needed
                        if iframe_src.startswith('//'):
                            iframe_src = 'https:' + iframe_src
                        elif iframe_src.startswith('/'):
                            iframe_src = referer_url.rstrip('/') + iframe_src
                        
                        # Special handling for cache/links iframes (they contain stream links)
                        if 'cache/links' in iframe_src or '/links/' in iframe_src:
                            print(f"  ⚠️  Found cache/links iframe - fetching directly...")
                            print(f"  Fetching: {iframe_src}")
                            try:
                                # Fetch the links HTML directly
                                links_response = requests.get(iframe_src, headers=headers, timeout=10, verify=False)
                                print(f"  Response status: {links_response.status_code}")
                                
                                if links_response.status_code == 200:
                                    links_content = links_response.text
                                    print(f"  Content length: {len(links_content)} bytes")
                                    
                                    # Look for .m3u8 URLs in the links HTML
                                    m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
                                    links_matches = re.findall(m3u8_pattern, links_content)
                                    if links_matches:
                                        print(f"  ✓ Found {len(links_matches)} stream URL(s) in links HTML:")
                                        for match in links_matches[:5]:
                                            if match not in stream_urls:
                                                stream_urls.append(match)
                                                print(f"    {match}")
                                    else:
                                        print(f"  ⚠️  No .m3u8 URLs found in links HTML")
                                        # Debug: show first 500 chars of content
                                        print(f"  Content preview: {links_content[:500]}")
                                    
                                    # Look for webplayer.php and webplayer2.php links (including protocol-relative)
                                    webplayer_pattern = r'(?:https?:)?//[^\s"\'<>]+webplayer2?\.php[^\s"\'<>]*'
                                    webplayer_matches = re.findall(webplayer_pattern, links_content)
                                    if webplayer_matches:
                                        print(f"  ✓ Found {len(webplayer_matches)} webplayer link(s) in links HTML")
                                        for wp_url in webplayer_matches[:7]:
                                            # Make URL absolute if needed
                                            if wp_url.startswith('//'):
                                                wp_url = 'https:' + wp_url
                                            print(f"    {wp_url}")
                                            # Try to extract stream from this webplayer2 URL
                                            wp_stream = extract_stream_from_html(wp_url, iframe_src)
                                            if wp_stream and wp_stream not in stream_urls:
                                                stream_urls.append(wp_stream)
                                                print(f"      → Extracted: {wp_stream}")
                                    
                                    # Also look for href attributes with webplayer URLs
                                    href_pattern = r'href=["\']((?:https?:)?//[^\s"\'<>]+webplayer2?\.php[^\s"\'<>]*)["\']'
                                    href_matches = re.findall(href_pattern, links_content)
                                    if href_matches:
                                        print(f"  ✓ Found {len(href_matches)} webplayer href(s)")
                                        for href_url in href_matches[:7]:
                                            if href_url.startswith('//'):
                                                href_url = 'https:' + href_url
                                            if href_url not in [w.replace('https:', '') for w in webplayer_matches]:
                                                print(f"    {href_url}")
                                                wp_stream = extract_stream_from_html(href_url, iframe_src)
                                                if wp_stream and wp_stream not in stream_urls:
                                                    stream_urls.append(wp_stream)
                                                    print(f"      → Extracted: {wp_stream}")
                                    
                                    # Look for onclick handlers with URLs
                                    onclick_pattern = r'onclick=["\']([^"\']+)["\']'
                                    onclick_matches = re.findall(onclick_pattern, links_content)
                                    if onclick_matches:
                                        print(f"  ✓ Found {len(onclick_matches)} onclick handler(s)")
                                        for onclick in onclick_matches[:3]:
                                            if '.m3u8' in onclick or 'webplayer' in onclick:
                                                print(f"    {onclick[:100]}")
                                else:
                                    print(f"  ❌ Links iframe returned status {links_response.status_code}")
                            except Exception as e:
                                print(f"  ❌ Error fetching links iframe: {e}")
                                import traceback
                                traceback.print_exc()
                        
                        # Try to access iframe content frame
                        iframe_frame = iframe.content_frame()
                        if iframe_frame:
                            iframe_frame.wait_for_timeout(3000)
                            # Check iframe's network requests
                            print(f"    Waiting for iframe content...")
                except Exception as e:
                    print(f"  ⚠️  Error checking iframe: {e}")
            
            # Wait a bit more for any delayed requests
            page.wait_for_timeout(3000)
            
            browser.close()
            
            if stream_urls:
                return stream_urls[0]  # Return first stream found
            else:
                print("  ⚠️  No .m3u8 URLs captured")
                return None
                
    except Exception as e:
        print(f"  ❌ Playwright error: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_stream_from_apl385_player(player_url, referer_url):
    """Extract stream from emb.apl385.me player"""
    print(f"\n[APL385] Extracting from player: {player_url}")
    
    headers = HEADERS.copy()
    headers['Referer'] = referer_url
    
    try:
        # First, try to get the HTML
        response = requests.get(player_url, headers=headers, timeout=10, verify=False)
        if response.status_code != 200:
            print(f"  ❌ Status code: {response.status_code}")
            return None
        
        content = response.text
        print(f"  Content length: {len(content)} bytes")
        
        # Look for .m3u8 URLs in the HTML
        m3u8_pattern = r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
        m3u8_matches = re.findall(m3u8_pattern, content)
        
        # Make URLs absolute
        absolute_matches = []
        for match in m3u8_matches:
            if match.startswith('//'):
                match = 'https:' + match
            absolute_matches.append(match)
        
        if absolute_matches:
            print(f"  ✓ Found {len(absolute_matches)} .m3u8 URL(s):")
            for match in absolute_matches[:3]:
                print(f"    {match}")
            return absolute_matches[0]
        
        # Look for JavaScript variables that might contain stream URLs
        js_patterns = [
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'src\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'url\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'stream\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, content, re.I)
            for match in matches:
                if '.m3u8' in match:
                    if match.startswith('//'):
                        match = 'https:' + match
                    elif not match.startswith('http'):
                        continue
                    print(f"  ✓ Found stream in JS: {match}")
                    return match
        
        # Look for iframe src that might contain the stream
        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
        iframe_matches = re.findall(iframe_pattern, content, re.I)
        for iframe_src in iframe_matches:
            if '.m3u8' in iframe_src or 'stream' in iframe_src.lower():
                if iframe_src.startswith('//'):
                    iframe_src = 'https:' + iframe_src
                print(f"  ✓ Found stream iframe: {iframe_src}")
                # Recursively extract from iframe
                return extract_stream_from_apl385_player(iframe_src, player_url)
        
        # If Playwright is available, use it to handle JavaScript/redirects
        if PLAYWRIGHT_AVAILABLE:
            print(f"  ⚠️  No direct stream found, trying Playwright...")
            return extract_stream_from_apl385_with_playwright(player_url, referer_url)
        
        print(f"  ⚠️  No stream URL found in HTML")
        return None
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_stream_from_apl385_with_playwright(player_url, referer_url, timeout=30000):
    """Extract stream from APL385 player using Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        return None
    
    print(f"  [Playwright] Loading player page...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS['User-Agent'],
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.set_extra_http_headers({'Referer': referer_url})
            
            stream_urls = []
            
            def handle_response(response):
                url = response.url
                if '.m3u8' in url:
                    if url not in stream_urls:
                        stream_urls.append(url)
                        print(f"    ✓ Found stream: {url}")
            
            page.on('response', handle_response)
            
            # Navigate to player
            page.goto(player_url, wait_until='domcontentloaded', timeout=timeout)
            
            # Wait for ad to potentially close/redirect
            print(f"  Waiting for page to load (handling ads/redirects)...")
            page.wait_for_timeout(5000)
            
            # Look for close ad button and click it if found
            try:
                close_selectors = [
                    'button:has-text("close")',
                    'button:has-text("Close")',
                    '[class*="close"]',
                    '[id*="close"]',
                    'a:has-text("click here")'
                ]
                for selector in close_selectors:
                    try:
                        close_btn = page.query_selector(selector)
                        if close_btn:
                            print(f"  Clicking close/continue button...")
                            close_btn.click()
                            page.wait_for_timeout(2000)
                            break
                    except:
                        pass
            except:
                pass
            
            # Wait for stream to load
            page.wait_for_timeout(5000)
            
            # Check page content for stream URLs
            page_content = page.content()
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
                print(f"  ⚠️  No stream URLs captured")
                return None
                
    except Exception as e:
        print(f"  ❌ Playwright error: {e}")
        return None

def extract_stream_from_html(webplayer_url, referer_url, silent=False):
    """Try to extract stream URL from HTML response"""
    if not silent:
        print(f"\n[HTML] Extracting stream from: {webplayer_url}")
    
    headers = HEADERS.copy()
    headers['Referer'] = referer_url
    
    try:
        response = requests.get(webplayer_url, headers=headers, timeout=10, verify=False)
        if response.status_code != 200:
            if not silent:
                print(f"  ❌ Status code: {response.status_code}")
            return None
        
        # Check if this is a webplayer that embeds APL385/APL386 player
        if ('webplayer2.php' in webplayer_url or 'webplayer.iframe.php' in webplayer_url) and 'apl38' not in webplayer_url:
            # Look for emb.apl385.me or emb.apl386.me iframe/embed (multiple patterns)
            apl385_patterns = [
                r'(?:https?:)?//emb\.apl38[56]\.me/[^\s"\'<>]+',
                r'emb\.apl38[56]\.me/player/[^\s"\'<>]+',
                r'src=["\']([^"\']*emb\.apl38[56]\.me[^"\']*)["\']',
                r'iframe[^>]+src=["\']([^"\']*apl38[56][^"\']*)["\']',
            ]
            
            for pattern in apl385_patterns:
                apl385_matches = re.findall(pattern, response.text, re.I)
                if apl385_matches:
                    if not silent:
                        print(f"  ✓ Found APL385/APL386 player embed")
                    # Get the first match (might be full match or group)
                    apl385_url = apl385_matches[0] if isinstance(apl385_matches[0], str) else apl385_matches[0]
                    # Clean up URL (remove newlines/whitespace)
                    apl385_url = re.sub(r'\s+', '', apl385_url)
                    # Make URL absolute
                    if apl385_url.startswith('//'):
                        apl385_url = 'https:' + apl385_url
                    elif not apl385_url.startswith('http'):
                        apl385_url = 'https://' + apl385_url
                    
                    if not silent:
                        print(f"    APL385/APL386 URL: {apl385_url}")
                    # Extract from APL385 player
                    apl385_stream = extract_stream_from_apl385_player(apl385_url, webplayer_url)
                    if apl385_stream:
                        return apl385_stream
                    break
        
        # Look for .m3u8 URLs in the HTML (including protocol-relative)
        m3u8_pattern = r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
        matches = re.findall(m3u8_pattern, response.text)
        
        # Make URLs absolute
        absolute_matches = []
        for match in matches:
            if match.startswith('//'):
                match = 'https:' + match
            absolute_matches.append(match)
        
        if absolute_matches:
            if not silent:
                print(f"  ✓ Found {len(absolute_matches)} .m3u8 URL(s) in HTML:")
                for i, match in enumerate(absolute_matches[:3], 1):
                    print(f"    {i}. {match}")
            return absolute_matches[0]
        else:
            if not silent:
                print("  ⚠️  No .m3u8 URLs found in HTML (may need Playwright)")
            return None
            
    except Exception as e:
        if not silent:
            print(f"  ❌ Error: {e}")
        return None

def main():
    """Main extraction function"""
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://livetv872.me/enx/eventinfo/332240466_philadelphia_san_francisco/#webplayer_alieztv|245753|332240466|2914683|142|27|en"
    
    print("\n" + "="*60)
    print("LiveTV872.me Stream Extraction from Hash Fragment")
    print("="*60)
    print(f"\nURL: {test_url}\n")
    
    # Parse hash fragment
    params = parse_hash_fragment(test_url)
    if not params:
        print("❌ Failed to parse hash fragment")
        return
    
    print("✓ Parsed parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    # Construct webplayer URLs (try iframe, webplayer2, and webplayer.php)
    base_url = test_url.split('#')[0]
    iframe_url = construct_webplayer_url(params, use_iframe=True)
    webplayer_url = construct_webplayer_url(params)
    webplayer2_url = construct_webplayer_url(params, use_webplayer2=True)
    
    print(f"\n✓ Webplayer.iframe URL: {iframe_url}")
    print(f"✓ Webplayer2 URL: {webplayer2_url}")
    print(f"✓ Webplayer URL: {webplayer_url}")
    print(f"✓ Referer: {base_url}")
    
    # Try direct APL385 player extraction first (if we have channel ID)
    if params.get('provider') == 'alieztv' or 'alieztv' in test_url.lower():
        print(f"\n[Step 1] Trying direct APL385 player (channel {params['channel_id']})...")
        apl385_url = f"https://emb.apl385.me/player/live.php?id={params['channel_id']}&w=728&h=480"
        stream_url = extract_stream_from_apl385_player(apl385_url, base_url)
    
    # Try webplayer.iframe.php first (it's often the most direct)
    if not stream_url:
        print(f"\n[Step 2] Trying webplayer.iframe.php...")
        stream_url = extract_stream_from_html(iframe_url, base_url)
    
    # Try HTML extraction from webplayer2 (it embeds APL385)
    if not stream_url:
        print(f"\n[Step 3] Trying webplayer2.php (may embed APL385)...")
        stream_url = extract_stream_from_html(webplayer2_url, base_url)
    
    # If that fails, try webplayer.php
    if not stream_url:
        print(f"\n[Step 4] Trying webplayer.php...")
        stream_url = extract_stream_from_html(webplayer_url, base_url)
    
    # If HTML extraction failed, try Playwright (which will also check cache/links)
    # Try iframe first with Playwright as it's most likely to work
    if not stream_url and PLAYWRIGHT_AVAILABLE:
        print("\n[Step 5] HTML extraction didn't find stream, trying Playwright with iframe...")
        stream_url = extract_stream_with_playwright(iframe_url, base_url)
    
    # Fallback to webplayer2 with Playwright
    if not stream_url and PLAYWRIGHT_AVAILABLE:
        print("\n[Step 6] Trying Playwright with webplayer2...")
        stream_url = extract_stream_with_playwright(webplayer2_url, base_url)
    
    # Results
    print("\n" + "="*60)
    print("Results")
    print("="*60)
    
    if stream_url:
        print(f"\n✅ Stream URL found:")
        print(f"   {stream_url}")
        print(f"\nTo play with VLC:")
        print(f"   vlc '{stream_url}'")
        print(f"\nTo play with ffplay:")
        print(f"   ffplay '{stream_url}'")
        print(f"\nTo play with mpv:")
        print(f"   mpv '{stream_url}'")
    else:
        print(f"\n❌ Could not extract stream URL")
        print(f"\nWebplayer URL (try in browser):")
        print(f"   {webplayer_url}")
        if not PLAYWRIGHT_AVAILABLE:
            print(f"\n💡 Tip: Install Playwright for better extraction:")
            print(f"   pip install playwright && playwright install")

if __name__ == '__main__':
    main()
