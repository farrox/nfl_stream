#!/usr/bin/env python3
"""
Dedicated test script for LiveTV872.me URLs with hash fragments
Tests: https://livetv872.me/enx/eventinfo/332240466_philadelphia_san_francisco/#webplayer_alieztv|245753|332240466|2914683|142|27|en
"""

import re
import requests
import urllib.parse
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def parse_hash_fragment(url):
    """Parse webplayer hash fragment from URL"""
    print(f"\n{'='*60}")
    print("Parsing Hash Fragment")
    print(f"{'='*60}")
    print(f"Original URL: {url}")
    
    if '#' not in url:
        print("❌ No hash fragment found in URL")
        return None
    
    hash_part = url.split('#', 1)[1]
    print(f"Hash fragment: {hash_part}")
    
    if not hash_part.startswith('webplayer_'):
        print("❌ Hash fragment doesn't start with 'webplayer_'")
        return None
    
    # Remove 'webplayer_' prefix and split by |
    parts = hash_part.replace('webplayer_', '').split('|')
    print(f"Parts: {parts}")
    
    if len(parts) < 7:
        print(f"❌ Expected 7 parts, got {len(parts)}")
        return None
    
    params = {
        'provider': parts[0],
        'channel_id': parts[1],
        'event_id': parts[2],
        'lid': parts[3],
        'ci': parts[4],
        'si': parts[5],
        'lang': parts[6]
    }
    
    print(f"\n✓ Parsed parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    return params

def construct_webplayer_url(params, cdn_domain='https://cdn.livetv872.me'):
    """Construct webplayer URL from parameters"""
    print(f"\n{'='*60}")
    print("Constructing Webplayer URL")
    print(f"{'='*60}")
    
    webplayer_url = (
        f"{cdn_domain}/webplayer.php?"
        f"t=ifr&"
        f"c={params['channel_id']}&"
        f"lang={params['lang']}&"
        f"eid={params['event_id']}&"
        f"lid={params['lid']}&"
        f"ci={params['ci']}&"
        f"si={params['si']}"
    )
    
    print(f"✓ Constructed URL: {webplayer_url}")
    return webplayer_url

def test_webplayer_url(webplayer_url, referer_url):
    """Test if webplayer URL is accessible"""
    print(f"\n{'='*60}")
    print("Testing Webplayer URL")
    print(f"{'='*60}")
    
    headers = HEADERS.copy()
    headers['Referer'] = referer_url
    
    try:
        print(f"Fetching: {webplayer_url}")
        print(f"Referer: {referer_url}")
        
        response = requests.get(webplayer_url, headers=headers, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Webplayer URL is accessible")
            
            # Check if it contains stream indicators
            content = response.text.lower()
            if '.m3u8' in content:
                print("✓ Found .m3u8 in response")
                # Try to extract m3u8 URLs
                m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
                matches = re.findall(m3u8_pattern, response.text)
                if matches:
                    print(f"✓ Found {len(matches)} potential stream URL(s):")
                    for i, match in enumerate(matches[:5], 1):
                        print(f"  {i}. {match}")
            
            # Check for iframe
            if 'iframe' in content:
                print("✓ Page contains iframe (may need Playwright for extraction)")
            
            # Check for JavaScript
            if 'script' in content:
                print("✓ Page contains JavaScript (may need Playwright for extraction)")
            
            return True
        else:
            print(f"❌ Webplayer URL returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webplayer URL: {e}")
        import traceback
        traceback.print_exc()
        return False

def extract_event_info(base_url):
    """Extract event information from the base URL"""
    print(f"\n{'='*60}")
    print("Extracting Event Info")
    print(f"{'='*60}")
    
    try:
        print(f"Fetching: {base_url}")
        response = requests.get(base_url, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract event ID from URL
        event_id_match = re.search(r'/eventinfo/(\d+)', base_url)
        if event_id_match:
            event_id = event_id_match.group(1)
            print(f"✓ Event ID from URL: {event_id}")
        
        # Look for title
        title_elem = soup.find('title')
        if title_elem:
            print(f"✓ Page title: {title_elem.get_text()}")
        
        # Look for webplayer links on the page
        all_links = soup.find_all('a', href=True)
        webplayer_links = [link for link in all_links if 'webplayer.php' in link.get('href', '')]
        print(f"✓ Found {len(webplayer_links)} webplayer link(s) on page")
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting event info: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    test_url = "https://livetv872.me/enx/eventinfo/332240466_philadelphia_san_francisco/#webplayer_alieztv|245753|332240466|2914683|142|27|en"
    
    print("\n" + "="*60)
    print("LiveTV872.me Hash Fragment Test")
    print("="*60)
    
    # Step 1: Parse hash fragment
    params = parse_hash_fragment(test_url)
    if not params:
        print("\n❌ Failed to parse hash fragment")
        return
    
    # Step 2: Construct webplayer URL
    base_url = test_url.split('#')[0]
    webplayer_url = construct_webplayer_url(params)
    
    # Step 3: Test webplayer URL
    test_webplayer_url(webplayer_url, base_url)
    
    # Step 4: Extract event info
    extract_event_info(base_url)
    
    # Step 5: Try alternative CDN domains
    print(f"\n{'='*60}")
    print("Testing Alternative CDN Domains")
    print(f"{'='*60}")
    
    cdn_domains = [
        'https://cdn.livetv872.me',
        'https://cdn.livetv869.me',
        'https://cdn.livetv868.me'
    ]
    
    for cdn in cdn_domains:
        alt_url = construct_webplayer_url(params, cdn)
        print(f"\nTesting {cdn}...")
        test_webplayer_url(alt_url, base_url)
    
    print(f"\n{'='*60}")
    print("Test Complete")
    print(f"{'='*60}")
    print(f"\nConstructed Webplayer URL:")
    print(f"  {webplayer_url}")
    print(f"\nUse this URL in your stream player or test with:")
    print(f"  curl -H 'Referer: {base_url}' '{webplayer_url}'")

if __name__ == '__main__':
    main()
