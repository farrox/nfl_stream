#!/usr/bin/env python3
"""Standalone script to trace a stream URL through the iframe chain"""

import requests
from bs4 import BeautifulSoup
import urllib3
import re
import json
from playwright.sync_api import sync_playwright
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

urllib3.disable_warnings()

def trace_stream(webplayer_url):
    """Trace the stream URL through the iframe chain"""
    print('=' * 80)
    print('TRACING STREAM URL')
    print('=' * 80)
    print(f'Starting URL: {webplayer_url}\n')
    
    stream_urls = []
    referer = None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            def handle_response(response):
                url = response.url
                if '.m3u8' in url.lower():
                    if url not in stream_urls:
                        stream_urls.append(url)
                        req = response.request
                        nonlocal referer
                        referer = req.headers.get('referer', 'https://exposestrat.com/')
                        print(f'✓ Captured .m3u8: {url[:100]}...')
                        print(f'  Referer: {referer}')
            
            page.on('response', handle_response)
            
            print('Step 1: Loading webplayer.php...')
            page.goto(webplayer_url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(3000)
            
            # Hide popups
            page.evaluate("""
                document.querySelectorAll('*[id*="flash"], *[id*="popup"], *[id*="overlay"], #localpp').forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                });
            """)
            
            print('Step 2: Waiting for iframes to load and stream requests...')
            
            # Try to click on video/player elements to trigger stream loading
            try:
                # Look for video elements
                video_elements = page.query_selector_all('video')
                if video_elements:
                    print(f'  Found {len(video_elements)} video element(s), trying to interact...')
                    for video in video_elements:
                        try:
                            video.click()
                            page.wait_for_timeout(1000)
                        except:
                            pass
                
                # Look for play buttons
                play_buttons = page.query_selector_all('button[class*="play"], div[class*="play"], a[class*="play"]')
                if play_buttons:
                    print(f'  Found {len(play_buttons)} play button(s), clicking...')
                    for btn in play_buttons[:3]:
                        try:
                            btn.click()
                            page.wait_for_timeout(1000)
                        except:
                            pass
            except Exception as e:
                print(f'  Error interacting with page: {e}')
            
            # Wait longer for nested iframes and JavaScript execution
            for i in range(15):
                page.wait_for_timeout(3000)
                if stream_urls:
                    break
                print(f'  Waiting... ({i+1}/15)')
                
                # Periodically try clicking again
                if i % 3 == 0:
                    try:
                        video_elements = page.query_selector_all('video')
                        for video in video_elements:
                            try:
                                video.click()
                            except:
                                pass
                    except:
                        pass
            
            # Check all pages (main + popups)
            all_pages = context.pages
            print(f'\nStep 3: Checking {len(all_pages)} page(s) for streams...')
            for i, check_page in enumerate(all_pages, 1):
                try:
                    page_content = check_page.content()
                    m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                    content_matches = re.findall(m3u8_pattern, page_content)
                    for match in content_matches:
                        if match not in stream_urls and not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ']):
                            stream_urls.append(match)
                            print(f'  ✓ Found .m3u8 in page {i} content: {match[:100]}...')
                except:
                    pass
            
            browser.close()
    
    except Exception as e:
        print(f'✗ Error: {e}')
        import traceback
        traceback.print_exc()
    
    if stream_urls:
        print(f'\n' + '=' * 80)
        print('✓ SUCCESS! Found stream URL(s)')
        print('=' * 80)
        for i, url in enumerate(stream_urls, 1):
            print(f'\nStream {i}: {url}')
            print(f'Referer: {referer or "https://exposestrat.com/"}')
            
            # Test accessibility
            try:
                headers = {
                    'Referer': referer or 'https://exposestrat.com/',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                r = requests.get(url, headers=headers, timeout=10, verify=False, stream=True)
                print(f'  Status: {r.status_code}')
                if r.status_code == 200:
                    print(f'  ✓ Stream is accessible!')
                    content = r.text[:200] if hasattr(r, 'text') else str(r.content[:200])
                    print(f'  Preview: {content[:100]}...')
                else:
                    print(f'  ✗ Stream returned {r.status_code}')
            except Exception as e:
                print(f'  ✗ Error testing stream: {e}')
        
        return stream_urls[0], referer or 'https://exposestrat.com/'
    else:
        print(f'\n✗ FAILED - No stream URL found')
        return None, None

if __name__ == '__main__':
    # Try webplayer.php first
    test_url = 'https://cdn.livetv869.me/webplayer.php?t=ifr&c=2904821&lang=en&eid=325575814&lid=2904821&ci=142&si=27'
    print('Trying webplayer.php version...\n')
    stream_url, referer = trace_stream(test_url)
    
    # If that fails, try webplayer2.php
    if not stream_url:
        print('\n' + '=' * 80)
        print('Trying webplayer2.php version...\n')
        test_url2 = test_url.replace('webplayer.php', 'webplayer2.php')
        stream_url, referer = trace_stream(test_url2)
    
    if stream_url:
        print(f'\n\nFinal Result:')
        print(f'Stream URL: {stream_url}')
        print(f'Referer: {referer}')
    else:
        print(f'\n\n✗ Could not find stream URL')
        print('This link may not have an active stream, or it requires special handling.')
