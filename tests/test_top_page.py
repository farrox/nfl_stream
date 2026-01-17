#!/usr/bin/env python3
"""
Test script to trace steps from https://livetv.sx/enx/allupcomingsports/27/
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Configuration
TOP_URL = "https://livetv.sx/enx/allupcomingsports/27/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print("="*80)
print("TRACING STEPS FROM TOP PAGE")
print("="*80)
print(f"\n📄 Step 1: Fetching top page: {TOP_URL}\n")

try:
    response = requests.get(TOP_URL, headers=HEADERS, timeout=10, verify=False)
    response.raise_for_status()
    print(f"✓ Status: {response.status_code}")
    print(f"✓ Content length: {len(response.text)} bytes")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(f"\n📊 Step 2: Analyzing page content\n")
    
    # Find all links
    all_links = soup.find_all('a', href=True)
    print(f"Total links found: {len(all_links)}")
    
    # Filter for eventinfo links and deduplicate by event ID
    eventinfo_links = []
    seen_event_ids = set()
    
    for link in all_links:
        href = link.get('href', '')
        if '/eventinfo/' in href:
            # Make URL absolute
            if href.startswith('/'):
                full_url = urljoin("https://livetv.sx", href)
            elif not href.startswith('http'):
                full_url = urljoin(TOP_URL, href)
            else:
                full_url = href
            
            # Skip broken URLs
            if re.search(r'/eventinfo/\d+__?/', full_url):
                continue
            
            # Extract event ID for deduplication
            event_id_match = re.search(r'/eventinfo/(\d+)', full_url)
            if event_id_match:
                event_id = event_id_match.group(1)
                
                # Only add if we haven't seen this event ID before
                if event_id not in seen_event_ids:
                    seen_event_ids.add(event_id)
                    
                    # Get link text (prefer non-empty text)
                    link_text = link.get_text(strip=True)
                    
                    eventinfo_links.append({
                        'url': full_url,
                        'text': link_text,
                        'href': href,
                        'event_id': event_id
                    })
    
    print(f"\n📋 Step 3: Event links found\n")
    print(f"Total eventinfo links: {len(eventinfo_links)}")
    
    # Show first 20 events
    print(f"\n{'='*80}")
    print("FIRST 20 EVENT LINKS:")
    print(f"{'='*80}\n")
    
    for i, event in enumerate(eventinfo_links[:20], 1):
        event_id = event.get('event_id', 'N/A')
        
        print(f"{i:2d}. Event ID: {event_id}")
        print(f"    URL: {event['url']}")
        print(f"    Text: {event['text'][:80] if event['text'] else '(empty)'}")
        print()
    
    # Check for priority event
    priority_event_id = '314788282'
    priority_events = [e for e in eventinfo_links if priority_event_id in e['url']]
    
    print(f"\n{'='*80}")
    print("PRIORITY EVENT CHECK:")
    print(f"{'='*80}\n")
    
    if priority_events:
        print(f"✓ Found priority event (314788282):")
        for event in priority_events:
            print(f"  - {event['url']}")
            print(f"  - Text: {event['text']}")
    else:
        print(f"✗ Priority event (314788282) NOT found in results")
    
    # Check for Patriots-related events
    print(f"\n{'='*80}")
    print("PATRIOTS-RELATED EVENTS (UNIQUE):")
    print(f"{'='*80}\n")
    
    patriots_events = []
    for event in eventinfo_links:
        url_lower = event['url'].lower()
        text_lower = event['text'].lower()
        if 'patriots' in url_lower or 'patriots' in text_lower or 'new_england' in url_lower or 'tampa' in url_lower:
            patriots_events.append(event)
    
    if patriots_events:
        print(f"Found {len(patriots_events)} unique Patriots-related event(s):\n")
        for i, event in enumerate(patriots_events, 1):
            event_id = event.get('event_id', 'N/A')
            print(f"{i}. Event ID: {event_id}")
            print(f"   URL: {event['url']}")
            print(f"   Text: {event['text']}")
            print()
    else:
        print("No Patriots-related events found")
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total eventinfo links: {len(eventinfo_links)}")
    print(f"Priority event found: {'Yes' if priority_events else 'No'}")
    print(f"Patriots-related events: {len(patriots_events)}")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
