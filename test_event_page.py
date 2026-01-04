#!/usr/bin/env python3
"""
Test script to trace the next step: following the event link and extracting player links
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Configuration
EVENT_URL = "https://livetv.sx/enx/eventinfo/314788282_tampa_bay_buccaneers_new_england_patriots/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print("="*80)
print("STEP 2: FOLLOWING EVENT LINK AND EXTRACTING PLAYER LINKS")
print("="*80)
print(f"\n📄 Fetching event page: {EVENT_URL}\n")

try:
    response = requests.get(EVENT_URL, headers=HEADERS, timeout=15, verify=False)
    response.raise_for_status()
    print(f"✓ Status: {response.status_code}")
    print(f"✓ Content length: {len(response.text)} bytes")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(f"\n📊 Analyzing event page content\n")
    
    # Find all links
    all_links = soup.find_all('a', href=True)
    print(f"Total links found: {len(all_links)}")
    
    # Look for webplayer.php links
    webplayer_links = []
    for link in all_links:
        href = link.get('href', '')
        onclick = link.get('onclick', '')
        
        # Check href for webplayer.php
        if 'webplayer.php' in href:
            # Make URL absolute
            if href.startswith('//'):
                full_url = 'https:' + href
            elif href.startswith('/'):
                full_url = 'https://cdn.livetv869.me' + href
            elif not href.startswith('http'):
                full_url = 'https://cdn.livetv869.me/webplayer.php?' + href if '?' in href else 'https://cdn.livetv869.me/' + href
            else:
                full_url = href
            
            # Extract channel number
            channel_match = re.search(r'[&?]c=(\d+)', full_url)
            channel_id = channel_match.group(1) if channel_match else 'Unknown'
            
            webplayer_links.append({
                'url': full_url,
                'channel_id': channel_id,
                'source': 'href'
            })
        
        # Check onclick for webplayer.php
        if 'webplayer.php' in onclick:
            onclick_match = re.search(r'["\']([^"\']*webplayer\.php[^"\']*)["\']', onclick)
            if onclick_match:
                url_from_onclick = onclick_match.group(1)
                if url_from_onclick.startswith('//'):
                    full_url = 'https:' + url_from_onclick
                elif not url_from_onclick.startswith('http'):
                    full_url = 'https://cdn.livetv869.me/webplayer.php?' + url_from_onclick if '?' in url_from_onclick else 'https://cdn.livetv869.me/' + url_from_onclick
                else:
                    full_url = url_from_onclick
                
                # Check if we already have this URL
                if not any(wp['url'] == full_url for wp in webplayer_links):
                    channel_match = re.search(r'[&?]c=(\d+)', full_url)
                    channel_id = channel_match.group(1) if channel_match else 'Unknown'
                    webplayer_links.append({
                        'url': full_url,
                        'channel_id': channel_id,
                        'source': 'onclick'
                    })
    
    # Also check for webplayer.php in the HTML directly (regex)
    webplayer_pattern = r'//cdn\.livetv869\.me/webplayer\.php[^\s"\'\)]+'
    regex_matches = re.findall(webplayer_pattern, response.text)
    for match in regex_matches:
        full_url = 'https:' + match if match.startswith('//') else match
        if not any(wp['url'] == full_url for wp in webplayer_links):
            channel_match = re.search(r'[&?]c=(\d+)', full_url)
            channel_id = channel_match.group(1) if channel_match else 'Unknown'
            webplayer_links.append({
                'url': full_url,
                'channel_id': channel_id,
                'source': 'regex'
            })
    
    # Deduplicate by URL
    seen_urls = set()
    unique_webplayer_links = []
    for wp in webplayer_links:
        if wp['url'] not in seen_urls:
            seen_urls.add(wp['url'])
            unique_webplayer_links.append(wp)
    
    print(f"\n{'='*80}")
    print("WEBPLAYER LINKS FOUND:")
    print(f"{'='*80}\n")
    print(f"Total unique webplayer links: {len(unique_webplayer_links)}\n")
    
    for i, wp in enumerate(unique_webplayer_links, 1):
        print(f"{i:2d}. Channel {wp['channel_id']} (found via {wp['source']})")
        print(f"    URL: {wp['url']}")
        print()
    
    # Check for hidden links
    hidden_containers = soup.find_all(id=re.compile(r'hidden', re.I))
    print(f"\n{'='*80}")
    print("HIDDEN LINK CONTAINERS:")
    print(f"{'='*80}\n")
    print(f"Found {len(hidden_containers)} hidden container(s)")
    
    hidden_webplayer_links = []
    for container in hidden_containers:
        container_links = container.find_all('a', href=True)
        for link in container_links:
            href = link.get('href', '')
            if 'webplayer.php' in href:
                if href.startswith('//'):
                    full_url = 'https:' + href
                elif not href.startswith('http'):
                    full_url = 'https://cdn.livetv869.me/webplayer.php?' + href if '?' in href else 'https://cdn.livetv869.me/' + href
                else:
                    full_url = href
                
                channel_match = re.search(r'[&?]c=(\d+)', full_url)
                channel_id = channel_match.group(1) if channel_match else 'Unknown'
                
                if not any(wp['url'] == full_url for wp in hidden_webplayer_links):
                    hidden_webplayer_links.append({
                        'url': full_url,
                        'channel_id': channel_id
                    })
    
    if hidden_webplayer_links:
        print(f"\nFound {len(hidden_webplayer_links)} webplayer link(s) in hidden containers:")
        for wp in hidden_webplayer_links:
            print(f"  - Channel {wp['channel_id']}: {wp['url']}")
    
    # Summary
    all_webplayer_links = unique_webplayer_links + hidden_webplayer_links
    # Deduplicate again
    final_urls = set()
    final_links = []
    for wp in all_webplayer_links:
        if wp['url'] not in final_urls:
            final_urls.add(wp['url'])
            final_links.append(wp)
    
    print(f"\n{'='*80}")
    print("FINAL SUMMARY:")
    print(f"{'='*80}\n")
    print(f"Total unique webplayer links found: {len(final_links)}")
    print(f"Expected: 10 links")
    print(f"Status: {'✓ SUCCESS' if len(final_links) >= 10 else '✗ MISSING LINKS'}")
    
    if len(final_links) >= 10:
        print(f"\n✓ Found all 10+ player links!")
    else:
        print(f"\n⚠ Only found {len(final_links)} links (expected 10)")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

