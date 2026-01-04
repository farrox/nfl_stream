#!/usr/bin/env python3
"""
Test script to detect popup windows and fake "click to unmute" links
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test with the webplayer URL
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
print("TESTING POPUP DETECTION AND FAKE 'CLICK TO UNMUTE' LINKS")
print("="*80)
print(f"\n📄 Testing: {WEBPLAYER_URL}\n")

def analyze_page_for_popups(url, depth=0, max_depth=3):
    """Recursively analyze pages for popups and fake links"""
    indent = "  " * depth
    
    if depth > max_depth:
        return []
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        response.raise_for_status()
        print(f"{indent}✓ Fetched: {url} ({response.status_code}, {len(response.text)} bytes)")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        findings = []
        
        # 1. Check for window.open() calls (popup triggers)
        print(f"\n{indent}1️⃣ Checking for window.open() calls...")
        scripts = soup.find_all('script')
        popup_urls = []
        for script in scripts:
            script_text = script.string if script.string else ''
            # Find window.open calls
            window_open_patterns = [
                r'window\.open\(["\']([^"\']+)["\']',
                r'window\.open\(([^)]+)\)',
                r'open\(["\']([^"\']+)["\']',
            ]
            for pattern in window_open_patterns:
                matches = re.findall(pattern, script_text, re.IGNORECASE)
                for match in matches:
                    # Clean up the match
                    match = match.strip().strip('"\'')
                    if match and match.startswith('http'):
                        popup_url = normalize_url(match, url)
                        if popup_url not in popup_urls:
                            popup_urls.append(popup_url)
                            print(f"{indent}   ⚠ Found popup trigger: {popup_url}")
                            findings.append({
                                'type': 'popup_trigger',
                                'url': popup_url,
                                'source': url,
                                'depth': depth
                            })
        
        if not popup_urls:
            print(f"{indent}   ✓ No window.open() calls found")
        
        # 2. Check for "click to unmute" or similar text
        print(f"\n{indent}2️⃣ Checking for 'click to unmute' or similar fake link text...")
        unmute_keywords = [
            'click to unmute',
            'click here to unmute',
            'unmute',
            'click to play',
            'click to continue',
            'click here',
            'tap to unmute',
            'press to unmute',
            'click to start',
        ]
        
        # Check all text content (including in script tags that might be rendered)
        page_text = soup.get_text().lower()
        html_text = response.text.lower()
        
        unmute_elements = []
        for keyword in unmute_keywords:
            # Check in rendered text
            if keyword in page_text:
                # Find the element containing this text
                elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in elements:
                    parent = elem.parent
                    if parent:
                        # Check if it's a link or clickable element
                        is_clickable = (parent.name == 'a' or 
                                       parent.name == 'button' or
                                       parent.get('onclick') or
                                       parent.find('a') or
                                       parent.find('button'))
                        
                        if is_clickable:
                            link = parent.find('a') if parent.find('a') else (parent if parent.name == 'a' else None)
                            button = parent.find('button') if parent.find('button') else (parent if parent.name == 'button' else None)
                            
                            href = link.get('href', '') if link else ''
                            onclick = (link.get('onclick', '') if link else '') or (button.get('onclick', '') if button else '') or parent.get('onclick', '')
                            
                            full_url = normalize_url(href, url) if href else None
                            
                            unmute_elements.append({
                                'text': elem.strip(),
                                'href': full_url if full_url else href,
                                'onclick': onclick,
                                'parent_tag': parent.name,
                                'is_clickable': True
                            })
                            print(f"{indent}   ⚠ Found '{keyword}' in clickable element: {elem.strip()[:60]}")
                            if href:
                                print(f"{indent}      Link: {full_url if full_url else href}")
                            if onclick:
                                print(f"{indent}      OnClick: {onclick[:80]}")
            
            # Also check in raw HTML (might be in comments or hidden)
            if keyword in html_text:
                # Find context around the keyword
                matches = list(re.finditer(re.escape(keyword), html_text, re.IGNORECASE))
                for match in matches:
                    start = max(0, match.start() - 100)
                    end = min(len(response.text), match.end() + 100)
                    context = response.text[start:end]
                    if 'onclick' in context.lower() or '<a' in context.lower() or '<button' in context.lower():
                        print(f"{indent}   ⚠ Found '{keyword}' near clickable element in HTML")
                        print(f"{indent}      Context: {context[:120]}")
        
        if unmute_elements:
            findings.append({
                'type': 'fake_unmute_link',
                'elements': unmute_elements,
                'source': url,
                'depth': depth
            })
        else:
            print(f"{indent}   ✓ No 'click to unmute' text found")
        
        # 3. Check for onclick handlers that might trigger popups
        print(f"\n{indent}3️⃣ Checking for onclick handlers...")
        onclick_elements = soup.find_all(attrs={'onclick': True})
        suspicious_onclicks = []
        for elem in onclick_elements:
            onclick = elem.get('onclick', '')
            # Check for suspicious patterns
            if any(pattern in onclick.lower() for pattern in ['open', 'window', 'popup', 'redirect']):
                # Try to extract the URL from the onclick
                url_match = re.search(r'linkaddress\s*=\s*["\']([^"\']+)["\']', response.text, re.IGNORECASE)
                linkaddress = None
                if url_match:
                    linkaddress = normalize_url(url_match.group(1), url)
                    print(f"{indent}   ⚠ Found linkaddress variable: {linkaddress}")
                
                suspicious_onclicks.append({
                    'tag': elem.name,
                    'onclick': onclick,
                    'text': elem.get_text(strip=True)[:50],
                    'linkaddress': linkaddress
                })
                print(f"{indent}   ⚠ Suspicious onclick: {onclick[:100]}")
                print(f"{indent}      Element text: {elem.get_text(strip=True)[:60]}")
                
                # Check parent/child elements for "unmute" text
                parent_text = elem.parent.get_text() if elem.parent else ''
                if any(kw in parent_text.lower() for kw in ['unmute', 'click', 'play', 'continue']):
                    print(f"{indent}      ⚠ Parent contains unmute/click text!")
        
        if suspicious_onclicks:
            findings.append({
                'type': 'suspicious_onclick',
                'elements': suspicious_onclicks,
                'source': url,
                'depth': depth
            })
        else:
            print(f"{indent}   ✓ No suspicious onclick handlers found")
        
        # 4. Check for iframes and follow them
        print(f"\n{indent}4️⃣ Checking for iframes...")
        iframes = soup.find_all('iframe', src=True)
        valid_iframes = [url for url in [normalize_url(iframe.get('src'), url) for iframe in iframes] 
                        if url and '<?php' not in url and url.startswith('http')]
        
        if valid_iframes:
            print(f"{indent}   Found {len(valid_iframes)} valid iframe(s)")
            for iframe_url in valid_iframes:
                print(f"{indent}   → Following iframe: {iframe_url}")
                nested_findings = analyze_page_for_popups(iframe_url, depth + 1, max_depth)
                findings.extend(nested_findings)
        else:
            print(f"{indent}   ✓ No valid iframes found")
        
        # 5. Check for meta refresh redirects
        print(f"\n{indent}5️⃣ Checking for meta refresh redirects...")
        meta_refresh = soup.find('meta', attrs={'http-equiv': re.compile('refresh', re.I)})
        if meta_refresh:
            content = meta_refresh.get('content', '')
            print(f"{indent}   ⚠ Found meta refresh: {content}")
            findings.append({
                'type': 'meta_refresh',
                'content': content,
                'source': url,
                'depth': depth
            })
        else:
            print(f"{indent}   ✓ No meta refresh found")
        
        # 6. Check for the specific popup overlay div (localpp)
        print(f"\n{indent}6️⃣ Checking for popup overlay div (localpp)...")
        popup_overlay = soup.find('div', id=re.compile('localpp', re.I))
        if popup_overlay:
            onclick = popup_overlay.get('onclick', '')
            style = popup_overlay.get('style', '')
            print(f"{indent}   ⚠ Found popup overlay div!")
            print(f"{indent}      Style: {style[:100]}")
            print(f"{indent}      OnClick: {onclick[:150]}")
            
            # Try to find where linkaddress is set
            linkaddress_patterns = [
                r'linkaddress\s*=\s*["\']([^"\']+)["\']',
                r'linkaddress\s*=\s*([^;]+);',
            ]
            
            for pattern in linkaddress_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                for match in matches:
                    if match and match != '0':
                        popup_url = normalize_url(match.strip().strip('"\''), url)
                        print(f"{indent}      → Popup URL (linkaddress): {popup_url}")
                        findings.append({
                            'type': 'popup_overlay',
                            'url': popup_url,
                            'source': url,
                            'depth': depth,
                            'onclick': onclick
                        })
                        break
        else:
            print(f"{indent}   ✓ No popup overlay div found")
    
        # 7. Check for JavaScript redirects
        print(f"\n{indent}7️⃣ Checking for JavaScript redirects...")
        redirect_patterns = [
            r'location\.href\s*=\s*["\']([^"\']+)["\']',
            r'location\.replace\(["\']([^"\']+)["\']',
            r'window\.location\s*=\s*["\']([^"\']+)["\']',
        ]
        
        redirect_urls = []
        for script in scripts:
            script_text = script.string if script.string else ''
            for pattern in redirect_patterns:
                matches = re.findall(pattern, script_text, re.IGNORECASE)
                for match in matches:
                    redirect_url = normalize_url(match, url)
                    if redirect_url not in redirect_urls:
                        redirect_urls.append(redirect_url)
                        print(f"{indent}   ⚠ Found redirect: {redirect_url}")
                        findings.append({
                        'type': 'javascript_redirect',
                        'url': redirect_url,
                        'source': url,
                        'depth': depth
                    })
        
        if not redirect_urls:
            print(f"{indent}   ✓ No JavaScript redirects found")
        
        return findings
        
    except Exception as e:
        print(f"{indent}✗ Error: {e}")
        return []

# Run the analysis
all_findings = analyze_page_for_popups(WEBPLAYER_URL)

# Summary
print("\n" + "="*80)
print("SUMMARY OF FINDINGS")
print("="*80)

if all_findings:
    print(f"\n⚠ Found {len(all_findings)} suspicious finding(s):\n")
    
    popup_triggers = [f for f in all_findings if f['type'] == 'popup_trigger']
    fake_unmute = [f for f in all_findings if f['type'] == 'fake_unmute_link']
    suspicious_onclick = [f for f in all_findings if f['type'] == 'suspicious_onclick']
    redirects = [f for f in all_findings if f['type'] in ['meta_refresh', 'javascript_redirect']]
    
    if popup_triggers:
        print(f"🔴 Popup Triggers ({len(popup_triggers)}):")
        for finding in popup_triggers:
            print(f"   - {finding['url']} (from {finding['source']})")
        print()
    
    if fake_unmute:
        print(f"🔴 Fake 'Click to Unmute' Links ({len(fake_unmute)}):")
        for finding in fake_unmute:
            for elem in finding['elements']:
                print(f"   - Text: '{elem['text']}'")
                if elem.get('href'):
                    print(f"     Link: {elem['href']}")
                if elem.get('onclick'):
                    print(f"     OnClick: {elem['onclick'][:80]}")
        print()
    
    if suspicious_onclick:
        print(f"🟡 Suspicious OnClick Handlers ({len(suspicious_onclick)}):")
        for finding in suspicious_onclick:
            for elem in finding['elements']:
                print(f"   - {elem['tag']}: {elem['onclick'][:80]}")
                if elem.get('linkaddress'):
                    print(f"     → Popup URL: {elem['linkaddress']}")
                if elem.get('text'):
                    print(f"     → Element text: {elem['text']}")
        print()
    
    popup_overlays = [f for f in all_findings if f['type'] == 'popup_overlay']
    
    if popup_overlays:
        print(f"🔴 Popup Overlays ({len(popup_overlays)}):")
        for finding in popup_overlays:
            print(f"   - Popup URL: {finding['url']}")
            print(f"     Source: {finding['source']}")
            print(f"     OnClick: {finding['onclick'][:100]}")
        print()
    
    if redirects:
        print(f"🟡 Redirects ({len(redirects)}):")
        for finding in redirects:
            if finding['type'] == 'meta_refresh':
                print(f"   - Meta refresh: {finding['content']}")
            else:
                print(f"   - JavaScript redirect: {finding['url']}")
        print()
else:
    print("\n✓ No popups or fake links detected")

print("\n" + "="*80)

