#!/usr/bin/env python3
"""
Simplified test server focused on the one webplayer link we've been debugging
"""
import re
import requests
from flask import Flask, jsonify, render_template_string, Response, request
import urllib3
from urllib.parse import urljoin, quote, unquote
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Event URL to extract all 10 links from
EVENT_URL = "https://livetv.sx/enx/eventinfo/327480884_baltimore_new_england_patriots/"

# Store all player links
all_player_links = []

# Store extracted stream URL
extracted_stream_url = None
extracted_referer = "https://exposestrat.com/"
current_webplayer_url = None

# Import extraction function from parent directory
from extract_stream import extract_stream_with_playwright

SIMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Stream Player</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #fff;
            margin: 0;
            padding: 0;
        }
        .main-layout {
            display: flex;
            height: 100vh;
        }
        .sidebar {
            width: 300px;
            background: #2a2a2a;
            padding: 20px;
            overflow-y: auto;
            border-right: 2px solid #333;
        }
        .sidebar h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .link-item {
            background: #1a1a1a;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            cursor: pointer;
            border: 2px solid transparent;
            transition: all 0.2s;
        }
        .link-item:hover {
            border-color: #667eea;
            background: #222;
        }
        .link-item.active {
            border-color: #667eea;
            background: #2a2a2a;
        }
        .link-item.working {
            border-left: 4px solid #28a745;
        }
        .link-item.failed {
            border-left: 4px solid #dc3545;
        }
        .link-item.testing {
            border-left: 4px solid #ffc107;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .link-item .link-number {
            color: #667eea;
            font-weight: bold;
            margin-right: 8px;
        }
        .link-item .link-channel {
            font-size: 11px;
            color: #999;
            font-family: monospace;
            margin-top: 4px;
        }
        .content-area {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            margin-bottom: 20px;
            color: #667eea;
        }
        .info-box {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .info-box h2 {
            margin-bottom: 10px;
            color: #667eea;
        }
        .url-display {
            background: #1a1a1a;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
            margin: 10px 0;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 10px 10px 0;
        }
        button:hover {
            background: #5568d3;
        }
        button:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .status {
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .status.success {
            background: #28a745;
        }
        .status.error {
            background: #dc3545;
        }
        .status.info {
            background: #17a2b8;
        }
        #video {
            width: 100%;
            max-width: 1200px;
            background: #000;
            border-radius: 8px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="main-layout">
        <!-- Left Sidebar with Links -->
        <div class="sidebar">
            <h2>🎮 Load Game Links</h2>
            <div style="margin-bottom: 15px;">
                <input 
                    type="text" 
                    id="gameUrlInput" 
                    placeholder="Paste game link here..." 
                    style="width: 100%; padding: 10px; border-radius: 4px; border: 2px solid #444; background: #1a1a1a; color: #fff; font-size: 12px; margin-bottom: 8px;"
                    value="https://livetv.sx/enx/eventinfo/314788282_tampa_bay_buccaneers_new_england_patriots/"
                />
                <button onclick="loadLinksFromUrl()" style="width: 100%; margin-bottom: 8px;">🔍 Load Links from URL</button>
                <button onclick="loadAllLinks()" style="width: 100%; margin-bottom: 15px;">🔄 Reload Default Links</button>
            </div>
            <h2 style="margin-top: 20px;">📺 Available Links</h2>
            <div id="linksList">
                <div class="loading">Loading links...</div>
            </div>
        </div>
        
        <!-- Main Content Area -->
        <div class="content-area">
            <div class="container">
                <h1>🎥 Test Stream Player</h1>
                
                <div class="info-box">
                    <h2>Selected Webplayer URL</h2>
                    <div class="url-display" id="selectedUrl">No link selected</div>
                    <button onclick="extractStream()" id="extractBtn" disabled>🔍 Extract Stream URL</button>
                    <button onclick="loadStream()" id="loadBtn" disabled>▶️ Load Stream</button>
                    <div id="status"></div>
                </div>
                
                <div class="info-box" id="streamInfo" style="display: none;">
                    <h2>Extracted Stream URL</h2>
                    <div class="url-display" id="streamUrl"></div>
                    <div class="url-display">Referer: {{ extracted_referer }}</div>
                </div>
                
                <div id="videoContainer">
                    <video id="video" controls></video>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentStreamUrl = null;
        let currentWebplayerUrl = null;
        let allLinks = [];
        
        // Load all links on page load
        window.addEventListener('DOMContentLoaded', function() {
            const input = document.getElementById('gameUrlInput');
            if (input) {
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        loadLinksFromUrl();
                    }
                });
            }
            loadAllLinks();
        });
        
        async function loadAllLinks() {
            await loadLinksFromUrl(null);
        }
        
        async function loadLinksFromUrl(customUrl) {
            const linksList = document.getElementById('linksList');
            linksList.innerHTML = '<div class="loading">Loading links...</div>';
            
            if (!customUrl) {
                customUrl = document.getElementById('gameUrlInput').value.trim();
            }
            
            if (!customUrl) {
                customUrl = null;
            }
            
            try {
                let url = '/api/links';
                if (customUrl) {
                    url += '?url=' + encodeURIComponent(customUrl);
                }
                
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.success && data.links) {
                    allLinks = data.links;
                    renderLinks(data.links);
                    document.querySelector('.sidebar h2:last-of-type').textContent = `📺 Available Links (${data.links.length})`;
                } else {
                    linksList.innerHTML = '<div class="status error">Failed to load links: ' + (data.error || 'Unknown error') + '</div>';
                }
            } catch (error) {
                linksList.innerHTML = '<div class="status error">Error: ' + error.message + '</div>';
            }
        }
        
        function renderLinks(links) {
            const linksList = document.getElementById('linksList');
            linksList.innerHTML = '';
            
            if (links.length === 0) {
                linksList.innerHTML = '<div class="status error">No links found. Check the URL and try again.</div>';
                return;
            }
            
            links.forEach((link, index) => {
                const linkItem = document.createElement('div');
                linkItem.className = 'link-item';
                linkItem.innerHTML = `
                    <div>
                        <span class="link-number">#${index + 1}</span>
                        <span>Channel ${link.channel_id}</span>
                    </div>
                    <div class="link-channel">${link.url.substring(0, 60)}...</div>
                `;
                linkItem.onclick = () => selectLink(link, index);
                linksList.appendChild(linkItem);
            });
        }
        
        function selectLink(link, index) {
            document.querySelectorAll('.link-item').forEach((item, i) => {
                if (i === index) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
            
            currentWebplayerUrl = link.url;
            document.getElementById('selectedUrl').textContent = link.url;
            document.getElementById('extractBtn').disabled = false;
            document.getElementById('loadBtn').disabled = true;
            document.getElementById('streamInfo').style.display = 'none';
            currentStreamUrl = null;
            
            const video = document.getElementById('video');
            video.src = '';
            if (video.hls) {
                video.hls.destroy();
                video.hls = null;
            }
        }
        
        function markLinkStatus(index, status) {
            const linkItems = document.querySelectorAll('.link-item');
            if (linkItems[index]) {
                linkItems[index].classList.remove('testing', 'working', 'failed');
                if (status) {
                    linkItems[index].classList.add(status);
                }
            }
        }
        
        async function extractStream() {
            if (!currentWebplayerUrl) {
                alert('Please select a link first');
                return;
            }
            
            const currentIndex = allLinks.findIndex(l => l.url === currentWebplayerUrl);
            markLinkStatus(currentIndex, 'testing');
            
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = '<div class="status info">Extracting stream URL... This may take 30-60 seconds.</div>';
            
            try {
                const response = await fetch('/api/extract?url=' + encodeURIComponent(currentWebplayerUrl));
                const data = await response.json();
                
                if (data.success && data.stream_url) {
                    currentStreamUrl = data.stream_url;
                    document.getElementById('streamUrl').textContent = data.stream_url;
                    document.getElementById('streamInfo').style.display = 'block';
                    document.getElementById('loadBtn').disabled = false;
                    statusDiv.innerHTML = '<div class="status success">✓ Stream URL extracted successfully!</div>';
                    markLinkStatus(currentIndex, 'working');
                } else {
                    const errorMsg = data.error || 'Unknown error';
                    statusDiv.innerHTML = '<div class="status error">✗ Failed to extract stream URL: ' + errorMsg + '</div>';
                    console.error('Extraction failed:', data);
                    markLinkStatus(currentIndex, 'failed');
                    
                    if (data.details) {
                        console.error('Error details:', data.details);
                    }
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status error">✗ Error: ' + error.message + '</div>';
                markLinkStatus(currentIndex, 'failed');
            }
        }
        
        function loadStream() {
            if (!currentStreamUrl) {
                alert('Please extract stream URL first');
                return;
            }
            
            const video = document.getElementById('video');
            const statusDiv = document.getElementById('status');
            
            statusDiv.innerHTML = '<div class="status info">Loading stream...</div>';
            
            if (video.hls) {
                video.hls.destroy();
            }
            
            if (Hls.isSupported()) {
                const hls = new Hls();
                video.hls = hls;
                hls.loadSource('/stream.m3u8');
                hls.attachMedia(video);
                
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    video.play();
                    statusDiv.innerHTML = '<div class="status success">✓ Stream loaded and playing!</div>';
                });
                
                hls.on(Hls.Events.ERROR, function(event, data) {
                    if (data.fatal) {
                        statusDiv.innerHTML = '<div class="status error">✗ Stream error: ' + data.type + '</div>';
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = '/stream.m3u8';
                video.play();
                statusDiv.innerHTML = '<div class="status success">✓ Stream loaded (native HLS)!</div>';
            } else {
                statusDiv.innerHTML = '<div class="status error">✗ HLS not supported in this browser</div>';
            }
        }
    </script>
</body>
</html>
"""

def extract_player_links(event_url):
    """Extract all player links from event page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        if 'webplayer.php' in event_url or 'webplayer2.php' in event_url:
            print(f"[Extract Links] Detected direct player URL, returning as-is...")
            channel_match = re.search(r'[&?]c=(\d+)', event_url)
            channel_id = channel_match.group(1) if channel_match else 'direct'
            return [{
                'url': event_url,
                'channel_id': channel_id
            }]
        
        response = requests.get(event_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        player_links = []
        
        if 'rojadirectame.eu' in event_url:
            print(f"[Extract Links] Detected rojadirectame.eu, extracting iframe links...")
            iframes = soup.find_all('iframe', src=True)
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    if iframe_src.startswith('//'):
                        full_url = 'https:' + iframe_src
                    elif iframe_src.startswith('/'):
                        full_url = urljoin(event_url, iframe_src)
                    elif not iframe_src.startswith('http'):
                        full_url = urljoin(event_url, iframe_src)
                    else:
                        full_url = iframe_src
                    
                    channel_id = 'iframe'
                    if 'dunga' in full_url.lower():
                        channel_id = 'dungatv'
                    elif 'player' in full_url.lower():
                        channel_id = 'player'
                    
                    if not any(p['url'] == full_url for p in player_links):
                        player_links.append({
                            'url': full_url,
                            'channel_id': channel_id
                        })
            
            if not player_links:
                player_links.append({
                    'url': event_url,
                    'channel_id': 'main'
                })
            
            return player_links
        
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            if 'webplayer.php' in href or 'webplayer2.php' in href:
                if href.startswith('//'):
                    full_url = 'https:' + href
                elif href.startswith('/'):
                    full_url = 'https://cdn.livetv869.me' + href
                elif not href.startswith('http'):
                    if 'webplayer2.php' in href:
                        base = 'https://cdn.livetv869.me/webplayer2.php'
                    else:
                        base = 'https://cdn.livetv869.me/webplayer.php'
                    full_url = base + ('?' + href if '?' in href else '/' + href) if '?' in href or not href.startswith('/') else base + href
                else:
                    full_url = href
                
                channel_match = re.search(r'[&?]c=(\d+)', full_url)
                channel_id = channel_match.group(1) if channel_match else 'Unknown'
                
                if not any(p['url'] == full_url for p in player_links):
                    player_links.append({
                        'url': full_url,
                        'channel_id': channel_id
                    })
        
        webplayer_patterns = [
            r'//cdn\.livetv869\.me/webplayer\.php[^\s"\'\)]+',
            r'//cdn\.livetv869\.me/webplayer2\.php[^\s"\'\)]+',
            r'https?://cdn\.livetv869\.me/webplayer\.php[^\s"\'\)]+',
            r'https?://cdn\.livetv869\.me/webplayer2\.php[^\s"\'\)]+',
        ]
        for pattern in webplayer_patterns:
            matches = re.findall(pattern, response.text)
            for match in matches:
                if match.startswith('//'):
                    full_url = 'https:' + match
                else:
                    full_url = match
                channel_match = re.search(r'[&?]c=(\d+)', full_url)
                channel_id = channel_match.group(1) if channel_match else 'Unknown'
                if not any(p['url'] == full_url for p in player_links):
                    player_links.append({
                        'url': full_url,
                        'channel_id': channel_id
                    })
        
        return player_links
        
    except Exception as e:
        print(f"[Extract Links] Error: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.route('/')
def index():
    """Main page"""
    return render_template_string(
        SIMPLE_HTML,
        extracted_referer=extracted_referer
    )


@app.route('/api/links')
def api_links():
    """Get all player links from event page"""
    global all_player_links
    
    event_url = request.args.get('url', EVENT_URL)
    
    if not event_url or not event_url.startswith('http'):
        return jsonify({
            'success': False,
            'error': 'Invalid URL provided'
        }), 400
    
    print(f"[API] Extracting player links from: {event_url}")
    player_links = extract_player_links(event_url)
    print(f"[API] Found {len(player_links)} player links")
    
    if event_url == EVENT_URL:
        all_player_links = player_links
    
    if not player_links:
        return jsonify({
            'success': False,
            'error': 'No player links found. Make sure the URL is a valid event page (livetv.sx, rojadirectame.eu) or a direct player URL (webplayer.php, webplayer2.php).',
            'links': [],
            'count': 0
        }), 404
    
    return jsonify({
        'success': True,
        'links': player_links,
        'count': len(player_links),
        'event_url': event_url
    })


@app.route('/api/extract')
def api_extract():
    """Extract stream URL from webplayer"""
    global extracted_stream_url, extracted_referer, current_webplayer_url
    
    webplayer_url = request.args.get('url')
    if not webplayer_url:
        return jsonify({
            'success': False,
            'error': 'No webplayer URL provided'
        }), 400
    
    current_webplayer_url = webplayer_url
    print(f"\n[API] ========================================")
    print(f"[API] Extracting stream URL from:")
    print(f"[API] {webplayer_url}")
    print(f"[API] ========================================\n")
    
    try:
        stream_url, referer = extract_stream_with_playwright(webplayer_url)
        
        if stream_url:
            extracted_stream_url = stream_url
            extracted_referer = referer or "https://exposestrat.com/"
            print(f"\n[API] ✓ SUCCESS - Stream URL extracted")
            return jsonify({
                'success': True,
                'stream_url': stream_url,
                'referer': referer or "https://exposestrat.com/"
            })
        else:
            error_msg = 'Failed to extract stream URL. No .m3u8 URLs found.'
            print(f"\n[API] ✗ FAILED - {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'details': 'Check server console for detailed extraction logs'
            }), 500
    except Exception as e:
        error_msg = f'Extraction error: {str(e)}'
        print(f"\n[API] ✗ ERROR - {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/stream.m3u8')
def stream_proxy():
    """Proxy the M3U8 stream with correct referer"""
    global extracted_stream_url, extracted_referer
    
    if not extracted_stream_url:
        return jsonify({'error': 'No stream URL extracted. Please extract first.'}), 400
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': extracted_referer,
            'Origin': extracted_referer.rstrip('/')
        }
        response = requests.get(extracted_stream_url, headers=headers, timeout=10, verify=False)
        
        if response.status_code != 200:
            return jsonify({'error': f'Failed to fetch stream: {response.status_code}'}), response.status_code
        
        content = response.text
        base_url = extracted_stream_url.rsplit('/', 1)[0] + '/'
        lines = content.split('\n')
        rewritten_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if not line.startswith('http'):
                    segment_url = base_url + line
                else:
                    segment_url = line
                encoded_url = quote(segment_url, safe='')
                line = f'/proxy/{encoded_url}'
            rewritten_lines.append(line)
        
        return Response(
            '\n'.join(rewritten_lines),
            status=200,
            content_type='application/vnd.apple.mpegurl',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': '*',
                'Cache-Control': 'no-cache'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/<path:url>')
def proxy_segment(url):
    """Proxy stream segments"""
    global extracted_referer
    
    try:
        decoded_url = unquote(url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': extracted_referer,
            'Origin': extracted_referer.rstrip('/')
        }
        response = requests.get(decoded_url, headers=headers, timeout=10, stream=True, verify=False)
        
        return Response(
            response.iter_content(chunk_size=8192),
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'video/mp2t'),
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': '*'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("="*80)
    print("Simplified Test Server with 10 Links")
    print("="*80)
    print(f"\nEvent URL: {EVENT_URL}")
    print(f"\nServer starting on http://localhost:8080")
    print(f"\nInstructions:")
    print(f"  1. Open http://localhost:8080 in your browser")
    print(f"  2. Select a link from the left sidebar")
    print(f"  3. Click 'Extract Stream URL' (takes 30-60 seconds)")
    print(f"  4. Click 'Load Stream' to play")
    print("\n" + "="*80 + "\n")
    
    app.run(host='0.0.0.0', port=8080, debug=True)
