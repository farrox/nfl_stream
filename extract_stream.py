#!/usr/bin/env python3
"""
Script to extract stream URL from streamsgate.live
"""
import re
import requests
from bs4 import BeautifulSoup
import json

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
    url = "https://streamsgate.live/hd/hd-6.php"
    streams = extract_stream_url(url)
    
    if streams:
        print("\n" + "="*60)
        print("To play the stream, you can use:")
        print("="*60)
        print(f"\nVLC: vlc '{streams[0]}'")
        print(f"ffplay: ffplay '{streams[0]}'")
        print(f"mpv: mpv '{streams[0]}'")

