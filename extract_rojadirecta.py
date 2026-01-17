#!/usr/bin/env python3
"""
Extract stream from rojadirecta URLs using Playwright
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import sys

def extract_rojadirecta_stream(url, timeout=30000):
    """
    Extract stream URL from rojadirecta page.
    
    Args:
        url: rojadirecta event URL
        timeout: timeout in milliseconds
    
    Returns:
        Dictionary with stream URL and referer, or None if not found
    """
    print(f"\n{'='*60}")
    print("Extracting stream from rojadirecta")
    print('='*60)
    print(f"URL: {url}\n")
    
    stream_info = None
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Track stream URLs with their referer
            captured_streams = []
            
            def handle_request(request):
                url = request.url
                if '.m3u8' in url.lower():
                    headers = request.headers
                    referer = headers.get('referer', page.url)
                    info = {
                        'url': url,
                        'referer': referer,
                        'origin': headers.get('origin', ''),
                        'user_agent': headers.get('user-agent', '')
                    }
                    if info not in captured_streams:
                        captured_streams.append(info)
                        print(f"  ✓ Captured .m3u8 request: {url}")
                        print(f"     Referer: {referer}")
            
            def handle_response(response):
                url = response.url
                if '.m3u8' in url.lower():
                    request = response.request
                    headers = request.headers
                    referer = headers.get('referer', page.url)
                    info = {
                        'url': url,
                        'referer': referer,
                        'origin': headers.get('origin', ''),
                        'user_agent': headers.get('user-agent', '')
                    }
                    if info not in captured_streams:
                        captured_streams.append(info)
                        print(f"  ✓ Captured .m3u8 response: {url}")
                        print(f"     Referer: {referer}")
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # Navigate to rojadirecta page
            print("→ Loading rojadirecta page...")
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                page.wait_for_timeout(2000)
                
                # Find iframe with player
                print("→ Looking for player iframe...")
                iframes = page.query_selector_all('iframe')
                player_iframe_url = None
                
                for iframe in iframes:
                    src = iframe.get_attribute('src')
                    if src and ('dunga' in src.lower() or 'stream' in src.lower() or '.php' in src):
                        # Avoid ad iframes
                        if 'ad' not in src.lower() and 'banner' not in src.lower():
                            player_iframe_url = src
                            print(f"  ✓ Found player iframe: {src}")
                            break
                
                if player_iframe_url:
                    # Navigate to the iframe URL in the same page context
                    print(f"→ Loading player iframe...")
                    page.goto(player_iframe_url, wait_until='domcontentloaded', timeout=timeout)
                    page.wait_for_timeout(3000)
                    
                    # Handle popup overlays
                    try:
                        page.evaluate("""
                            const overlay = document.getElementById('localpp');
                            if (overlay) overlay.style.display = 'none';
                        """)
                    except:
                        pass
                    
                    # Close any popup windows
                    popup_count = 0
                    while popup_count < 10:
                        all_pages = context.pages
                        if len(all_pages) <= 1:
                            break
                        
                        for popup_page in all_pages:
                            if popup_page != page:
                                try:
                                    popup_page.close()
                                    popup_count += 1
                                    print(f"  → Closed popup {popup_count}")
                                except:
                                    pass
                        
                        page.wait_for_timeout(500)
                    
                    # Wait for stream to load
                    print("→ Waiting for stream to load...")
                    page.wait_for_timeout(5000)
                    
                    # Check for nested iframes
                    nested_iframes = page.query_selector_all('iframe')
                    if nested_iframes:
                        print(f"  → Found {len(nested_iframes)} nested iframes")
                    
                    # Wait for any delayed requests
                    page.wait_for_timeout(5000)
                
            except PlaywrightTimeoutError:
                print("  ⚠ Timeout, but checking captured URLs...")
            
            browser.close()
            
            # Return the first captured stream
            if captured_streams:
                stream_info = captured_streams[0]
                print(f"\n{'='*60}")
                print("SUCCESS!")
                print('='*60)
                print(f"Stream URL: {stream_info['url']}")
                print(f"Referer: {stream_info['referer']}")
            else:
                print(f"\n{'='*60}")
                print("No stream found")
                print('='*60)
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return stream_info

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_rojadirecta.py <rojadirecta_url>")
        print("\nExample:")
        print("  python extract_rojadirecta.py https://rojadirectame.eu/football/event-url")
        sys.exit(1)
    
    url = sys.argv[1]
    stream_info = extract_rojadirecta_stream(url)
    
    if stream_info:
        print("\n" + "="*60)
        print("Stream information:")
        print("="*60)
        print(f"URL: {stream_info['url']}")
        print(f"Referer: {stream_info['referer']}")
        print("\n" + "="*60)
        print("To test with curl:")
        print("="*60)
        print(f"curl -H 'Referer: {stream_info['referer']}' -H 'User-Agent: Mozilla/5.0' '{stream_info['url']}'")
        print("\n" + "="*60)
        print("To play with mpv:")
        print("="*60)
        print(f"mpv --http-header-fields='Referer: {stream_info['referer']}' '{stream_info['url']}'")
    else:
        print("\nFailed to extract stream URL")
        sys.exit(1)

if __name__ == "__main__":
    main()

