#!/usr/bin/env python3
"""
Test script for extracting stream from rojadirectame.eu
"""
from playwright.sync_api import sync_playwright
import re
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_rojadirecta(url):
    print(f"Testing: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to False to see what's happening
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        # Track all network requests
        stream_urls = []
        
        def handle_request(request):
            url = request.url
            if '.m3u8' in url.lower() or 'stream' in url.lower():
                print(f"[REQUEST] {url}")
                if '.m3u8' in url.lower() and url not in stream_urls:
                    stream_urls.append(url)
        
        def handle_response(response):
            url = response.url
            if '.m3u8' in url.lower():
                print(f"[RESPONSE] {url}")
                if url not in stream_urls:
                    stream_urls.append(url)
        
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        # Navigate to page
        print("Navigating to page...")
        page.goto(url, wait_until='networkidle', timeout=60000)
        
        # Wait for video to load
        print("Waiting for video player...")
        page.wait_for_timeout(5000)
        
        # Check for iframes
        iframes = page.query_selector_all('iframe')
        print(f"Found {len(iframes)} iframes")
        for i, iframe in enumerate(iframes):
            try:
                src = iframe.get_attribute('src')
                print(f"  Iframe {i+1}: {src}")
            except:
                pass
        
        # Try to find video elements
        videos = page.query_selector_all('video')
        print(f"Found {len(videos)} video elements")
        
        # Get page content and search for m3u8
        content = page.content()
        m3u8_matches = re.findall(r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*', content)
        if m3u8_matches:
            print(f"Found {len(m3u8_matches)} m3u8 URLs in page content:")
            for url in m3u8_matches:
                print(f"  - {url}")
                if url not in stream_urls:
                    stream_urls.append(url)
        
        # Wait a bit more for delayed requests
        print("Waiting for delayed requests...")
        page.wait_for_timeout(10000)
        
        browser.close()
        
        return stream_urls

if __name__ == "__main__":
    # Start from the rojadirecta URL
    start_url = "https://rojadirectame.eu/football/new-england-patriots-miami-dolphins-pxicc0je?l=1663029512"
    
    # First, extract the iframe
    print("Step 1: Extract iframe from rojadirecta page")
    from extract_stream import extract_stream_url
    iframes = extract_stream_url(start_url)
    
    if iframes:
        # Test the first iframe we found
        test_url = iframes[0]
        print(f"\n\nStep 2: Test iframe with Playwright: {test_url}")
        streams = test_rojadirecta(test_url)
        
        if streams:
            print(f"\n\n{'='*60}")
            print("SUCCESS! Found stream URLs:")
            print('='*60)
            for i, stream in enumerate(streams, 1):
                print(f"{i}. {stream}")
        else:
            print("\n\nNo stream URLs found")
