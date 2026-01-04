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
            // Set up Enter key handler for input
            const input = document.getElementById('gameUrlInput');
            if (input) {
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        loadLinksFromUrl();
                    }
                });
            }
            // Load default links
            loadAllLinks();
        });
        
        async function loadAllLinks() {
            await loadLinksFromUrl(null);
        }
        
        async function loadLinksFromUrl(customUrl) {
            const linksList = document.getElementById('linksList');
            linksList.innerHTML = '<div class="loading">Loading links...</div>';
            
            // Get URL from input if not provided
            if (!customUrl) {
                customUrl = document.getElementById('gameUrlInput').value.trim();
            }
            
            // If still no URL, use default
            if (!customUrl) {
                customUrl = null; // Will use default in backend
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
                    // Update the sidebar title with count
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
            // Update active state
            document.querySelectorAll('.link-item').forEach((item, i) => {
                if (i === index) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
            
            // Set current webplayer URL
            currentWebplayerUrl = link.url;
            document.getElementById('selectedUrl').textContent = link.url;
            document.getElementById('extractBtn').disabled = false;
            document.getElementById('loadBtn').disabled = true;
            document.getElementById('streamInfo').style.display = 'none';
            currentStreamUrl = null;
            
            // Clear video
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
            
            // Find which link index we're working with
            const currentIndex = allLinks.findIndex(l => l.url === currentWebplayerUrl);
            
            // Mark as testing
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
                    
                    // Show more details if available
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
            
            // Clean up previous HLS instance
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
        # Handle direct player URLs - if it's already a player URL, return it as-is
        if 'webplayer.php' in event_url or 'webplayer2.php' in event_url:
            print(f"[Extract Links] Detected direct player URL, returning as-is...")
            # Extract channel ID
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
        
        # Handle rojadirectame.eu - extract iframe links
        if 'rojadirectame.eu' in event_url:
            print(f"[Extract Links] Detected rojadirectame.eu, extracting iframe links...")
            iframes = soup.find_all('iframe', src=True)
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    # Make URL absolute
                    if iframe_src.startswith('//'):
                        full_url = 'https:' + iframe_src
                    elif iframe_src.startswith('/'):
                        from urllib.parse import urljoin
                        full_url = urljoin(event_url, iframe_src)
                    elif not iframe_src.startswith('http'):
                        from urllib.parse import urljoin
                        full_url = urljoin(event_url, iframe_src)
                    else:
                        full_url = iframe_src
                    
                    # Extract identifier from URL
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
                        print(f"[Extract Links] Found iframe: {full_url[:80]}...")
            
            # If no iframes found, return the main page URL for Playwright extraction
            if not player_links:
                player_links.append({
                    'url': event_url,
                    'channel_id': 'main'
                })
            
            return player_links
        
        # Handle livetv.sx - extract webplayer.php and webplayer2.php links
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            if 'webplayer.php' in href or 'webplayer2.php' in href:
                # Make URL absolute
                if href.startswith('//'):
                    full_url = 'https:' + href
                elif href.startswith('/'):
                    full_url = 'https://cdn.livetv869.me' + href
                elif not href.startswith('http'):
                    # Determine which player type
                    if 'webplayer2.php' in href:
                        base = 'https://cdn.livetv869.me/webplayer2.php'
                    else:
                        base = 'https://cdn.livetv869.me/webplayer.php'
                    full_url = base + ('?' + href if '?' in href else '/' + href) if '?' in href or not href.startswith('/') else base + href
                else:
                    full_url = href
                
                # Extract channel ID
                channel_match = re.search(r'[&?]c=(\d+)', full_url)
                channel_id = channel_match.group(1) if channel_match else 'Unknown'
                
                # Deduplicate
                if not any(p['url'] == full_url for p in player_links):
                    player_links.append({
                        'url': full_url,
                        'channel_id': channel_id
                    })
        
        # Also check for webplayer.php and webplayer2.php in HTML directly
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


def extract_stream_with_playwright(webplayer_url, timeout=60000, max_popup_closes=15, allow_fallback=True):
    """Extract stream URL using Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        print("[Extract] Playwright not available")
        return None, None
    
    stream_urls = []
    referer = None
    error_message = None
    
    try:
        print(f"[Extract] Starting extraction from: {webplayer_url}")
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
                        print(f"[Extract] ✓ Captured .m3u8: {url[:80]}...")
                        print(f"[Extract]   Referer: {referer}")
            
            page.on('response', handle_response)
            
            print(f"[Extract] Navigating to page...")
            page.goto(webplayer_url, wait_until='domcontentloaded', timeout=timeout)
            print(f"[Extract] Page loaded, waiting for JavaScript...")
            page.wait_for_timeout(2000)
            
            # Function to hide Flash and other popups
            def hide_flash_popups():
                try:
                    result = page.evaluate("""
                        () => {
                            let hidden = 0;
                            
                            // Hide Flash-related popups by ID/class
                            const flashSelectors = [
                                '*[id*="flash"]',
                                '*[id*="Flash"]',
                                '*[id*="FLASH"]',
                                '*[class*="flash"]',
                                '*[class*="Flash"]',
                                '*[class*="FLASH"]',
                                '*[id*="install"]',
                                '*[id*="Install"]',
                                '*[class*="install"]',
                                '*[class*="Install"]',
                                '#localpp',
                                '.popup',
                                '.overlay',
                                '[class*="popup"]',
                                '[class*="overlay"]',
                                '[id*="popup"]',
                                '[id*="overlay"]'
                            ];
                            
                            // Hide specific popup overlays
                            flashSelectors.forEach(selector => {
                                try {
                                    const elements = document.querySelectorAll(selector);
                                    elements.forEach(el => {
                                        el.style.display = 'none';
                                        el.style.visibility = 'hidden';
                                        el.style.opacity = '0';
                                        el.style.zIndex = '-9999';
                                        el.style.pointerEvents = 'none';
                                        hidden++;
                                    });
                                } catch(e) {}
                            });
                            
                            // Try to find and hide elements containing "flash" or "install" in text
                            const allElements = document.querySelectorAll('div, span, p, a, button');
                            allElements.forEach(el => {
                                const text = (el.textContent || '').toLowerCase();
                                const id = (el.id || '').toLowerCase();
                                const className = (el.className || '').toLowerCase();
                                
                                if (text.includes('install flash') || 
                                    text.includes('flash player') ||
                                    text.includes('adobe flash') ||
                                    id.includes('flash') ||
                                    className.includes('flash')) {
                                    el.style.display = 'none';
                                    el.style.visibility = 'hidden';
                                    el.style.opacity = '0';
                                    el.style.zIndex = '-9999';
                                    el.style.pointerEvents = 'none';
                                    hidden++;
                                }
                            });
                            
                            // Click close buttons
                            const closeSelectors = [
                                '.close',
                                '.close-btn',
                                '[class*="close"]',
                                '[class*="Close"]',
                                '[id*="close"]',
                                '[id*="Close"]',
                                'button[aria-label*="close"]',
                                'button[aria-label*="Close"]'
                            ];
                            
                            closeSelectors.forEach(selector => {
                                try {
                                    const buttons = document.querySelectorAll(selector);
                                    buttons.forEach(btn => {
                                        const btnText = (btn.textContent || '').toLowerCase();
                                        if (btnText.includes('close') || btnText.includes('×') || btnText.includes('x')) {
                                            try {
                                                btn.click();
                                                hidden++;
                                            } catch(e) {}
                                        }
                                    });
                                } catch(e) {}
                            });
                            
                            // Also try to find and click any button with "close" text
                            const allButtons = document.querySelectorAll('button, a, div[onclick]');
                            allButtons.forEach(btn => {
                                const text = (btn.textContent || '').toLowerCase();
                                if (text.includes('close') || text === '×' || text === 'x') {
                                    try {
                                        btn.click();
                                        hidden++;
                                    } catch(e) {}
                                }
                            });
                            
                            return hidden;
                        }
                    """)
                    if result > 0:
                        print(f"[Extract] Hid {result} Flash/popup element(s)")
                except Exception as e:
                    print(f"[Extract] Error hiding Flash popups: {e}")
            
            # Hide popup overlay and Flash popups
            print(f"[Extract] Hiding popups and Flash overlays...")
            try:
                overlay = page.query_selector('#localpp')
                if overlay:
                    print(f"[Extract] Hiding popup overlay...")
                    page.evaluate("""
                        const overlay = document.getElementById('localpp');
                        if (overlay) overlay.style.display = 'none';
                    """)
            except Exception as e:
                print(f"[Extract] Could not hide overlay: {e}")
            
            # Hide Flash popups
            hide_flash_popups()
            page.wait_for_timeout(1000)
            
            # Try clicking on video player area to trigger stream load
            print(f"[Extract] Attempting to interact with page to trigger stream...")
            try:
                # Look for video elements or player containers
                video_elements = page.query_selector_all('video')
                if video_elements:
                    print(f"[Extract] Found {len(video_elements)} video element(s)")
                    # Try to click on first video to trigger play
                    try:
                        video_elements[0].click()
                        page.wait_for_timeout(1000)
                    except:
                        pass
                
                # Look for common player containers
                player_selectors = [
                    '#player', '.player', '[class*="player"]', 
                    '#video', '.video', '[class*="video"]',
                    'iframe[src*="player"]', 'iframe[src*="stream"]'
                ]
                for selector in player_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            print(f"[Extract] Found player element: {selector}")
                            # Try clicking it
                            try:
                                element.click()
                                page.wait_for_timeout(1000)
                            except:
                                pass
                            break
                    except:
                        pass
            except Exception as e:
                print(f"[Extract] Error interacting with page: {e}")
            
            # Close popups
            print(f"[Extract] Checking for popup windows...")
            popup_close_count = 0
            while popup_close_count < max_popup_closes:
                all_pages = context.pages
                if len(all_pages) <= 1:
                    break
                for popup_page in all_pages:
                    if popup_page != page:
                        try:
                            print(f"[Extract] Closing popup window {popup_close_count + 1}...")
                            popup_page.close()
                            popup_close_count += 1
                        except Exception as e:
                            print(f"[Extract] Error closing popup: {e}")
                page.wait_for_timeout(1000)
            
            if popup_close_count > 0:
                print(f"[Extract] Closed {popup_close_count} popup window(s)")
            
            # Wait for stream requests - try multiple times with interactions
            print(f"[Extract] Waiting for stream requests...")
            for wait_attempt in range(4):
                # Hide Flash popups at the start of each wait cycle
                hide_flash_popups()
                page.wait_for_timeout(5000)
                
                # Hide Flash popups again after waiting
                hide_flash_popups()
                
                # Try clicking/interacting again during wait
                if wait_attempt > 0:
                    try:
                        # Try clicking on any clickable elements that might trigger stream
                        clickable = page.query_selector('video, .play-button, [onclick*="play"], [onclick*="load"]')
                        if clickable:
                            try:
                                clickable.click()
                                print(f"[Extract] Clicked element to trigger stream...")
                                page.wait_for_timeout(1000)
                                # Hide popups again after clicking
                                hide_flash_popups()
                            except:
                                pass
                    except:
                        pass
                
                if stream_urls:
                    print(f"[Extract] ✓ Found stream after {wait_attempt + 1} wait cycle(s)")
                    break
                else:
                    print(f"[Extract] Waiting more... (attempt {wait_attempt + 2}/4)")
                    # Log what network requests we're seeing
                    print(f"[Extract]   (No .m3u8 URLs captured yet)")
            
            # Check all iframes for streams - recursively follow iframe chains
            print(f"[Extract] Checking iframes for streams...")
            def check_iframe_for_streams(current_page, depth=0, max_depth=3):
                """Recursively check iframes for stream URLs"""
                if depth > max_depth:
                    return
                
                try:
                    indent = "  " * depth
                    # Wait for iframes to load
                    current_page.wait_for_timeout(2000)
                    
                    # Check page content for m3u8 URLs
                    try:
                        page_content = current_page.content()
                        m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                        iframe_matches = re.findall(m3u8_pattern, page_content)
                        for match in iframe_matches:
                            if match not in stream_urls and not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ', 'Math.', 'Date.']):
                                stream_urls.append(match)
                                print(f"{indent}[Extract] ✓ Found .m3u8 in iframe content: {match[:80]}...")
                    except:
                        pass
                    
                    # Check for nested iframes
                    try:
                        iframes = current_page.query_selector_all('iframe')
                        if iframes:
                            print(f"{indent}[Extract] Found {len(iframes)} iframe(s) at depth {depth}")
                            for i, iframe in enumerate(iframes, 1):
                                try:
                                    iframe_src = iframe.get_attribute('src')
                                    if iframe_src:
                                        print(f"{indent}[Extract]   Iframe {i}: {iframe_src[:60]}...")
                                    
                                    # Try to get iframe content frame
                                    iframe_frame = iframe.content_frame()
                                    if iframe_frame:
                                        check_iframe_for_streams(iframe_frame, depth + 1, max_depth)
                                except Exception as e:
                                    print(f"{indent}[Extract]   Could not check iframe {i}: {e}")
                    except Exception as e:
                        print(f"{indent}[Extract] Error checking iframes: {e}")
                except Exception as e:
                    print(f"{indent}[Extract] Error in check_iframe_for_streams: {e}")
            
            try:
                iframes = page.query_selector_all('iframe')
                print(f"[Extract] Found {len(iframes)} iframe(s) on main page")
                for i, iframe in enumerate(iframes, 1):
                    try:
                        iframe_src = iframe.get_attribute('src')
                        if iframe_src:
                            print(f"[Extract] Checking iframe {i}/{len(iframes)}: {iframe_src[:60]}...")
                        
                        # Try to get iframe content frame
                        iframe_frame = iframe.content_frame()
                        if iframe_frame:
                            check_iframe_for_streams(iframe_frame, depth=0, max_depth=3)
                        else:
                            print(f"[Extract]   Could not access iframe content frame")
                    except Exception as e:
                        print(f"[Extract] Error checking iframe {i}: {e}")
            except Exception as e:
                print(f"[Extract] Error checking iframes: {e}")
            
            # Check if we found any streams
            if not stream_urls:
                print(f"[Extract] ⚠ No .m3u8 URLs captured in network requests")
                print(f"[Extract] Checking page content for stream URLs...")
                
                # Try to find stream URLs in page content
                page_content = page.content()
                m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                content_matches = re.findall(m3u8_pattern, page_content)
                for match in content_matches:
                    if match not in stream_urls and not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ', 'Math.', 'Date.']):
                        stream_urls.append(match)
                        print(f"[Extract] ✓ Found .m3u8 in page content: {match[:80]}...")
            
            # If still no streams, try to follow iframe chain
            if not stream_urls:
                print(f"[Extract] No streams found, checking iframe chain...")
                try:
                    iframes = page.query_selector_all('iframe[src]')
                    for i, iframe in enumerate(iframes):
                        try:
                            iframe_src = iframe.get_attribute('src')
                            if iframe_src and 'webplayer' not in iframe_src.lower() and 'ad' not in iframe_src.lower():
                                print(f"[Extract]   Checking iframe {i+1}: {iframe_src[:60]}...")
                                # Try to get iframe content
                                try:
                                    iframe_frame = iframe.content_frame()
                                    if iframe_frame:
                                        iframe_content = iframe_frame.content()
                                        m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                                        iframe_matches = re.findall(m3u8_pattern, iframe_content)
                                        for match in iframe_matches:
                                            if match not in stream_urls:
                                                stream_urls.append(match)
                                                print(f"[Extract] ✓ Found .m3u8 in iframe: {match[:80]}...")
                                except:
                                    pass
                        except:
                            pass
                except Exception as e:
                    print(f"[Extract] Error checking iframes: {e}")
            
            # Extract cache URL info before closing browser (for fallback)
            fallback_links = []
            if not stream_urls and allow_fallback:
                print(f"[Extract] Checking for cache HTML iframe with alternative player links...")
                try:
                    iframes = page.query_selector_all('iframe[src]')
                    for iframe in iframes:
                        try:
                            iframe_src = iframe.get_attribute('src')
                            if iframe_src and 'cache/links' in iframe_src:
                                print(f"[Extract]   Found cache HTML iframe: {iframe_src[:80]}...")
                                # Make URL absolute
                                if iframe_src.startswith('//'):
                                    cache_url = 'https:' + iframe_src
                                elif iframe_src.startswith('/'):
                                    cache_url = 'https://cdn.livetv869.me' + iframe_src
                                else:
                                    cache_url = iframe_src
                                
                                # Fetch the cache HTML to get webplayer2.php links
                                try:
                                    import requests
                                    cache_response = requests.get(cache_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
                                    if cache_response.status_code == 200:
                                        from bs4 import BeautifulSoup
                                        cache_soup = BeautifulSoup(cache_response.text, 'html.parser')
                                        cache_links = cache_soup.find_all('a', href=True)
                                        
                                        # Extract webplayer2.php links
                                        for link in cache_links:
                                            href = link.get('href', '')
                                            if 'webplayer2.php' in href:
                                                if href.startswith('//'):
                                                    full_url = 'https:' + href
                                                elif href.startswith('/'):
                                                    full_url = 'https://cdn.livetv869.me' + href
                                                elif not href.startswith('http'):
                                                    full_url = 'https://cdn.livetv869.me' + href
                                                else:
                                                    full_url = href
                                                if full_url not in fallback_links:
                                                    fallback_links.append(full_url)
                                        
                                        if fallback_links:
                                            print(f"[Extract]   Found {len(fallback_links)} webplayer2.php link(s) in cache")
                                except Exception as e:
                                    print(f"[Extract]   Error fetching cache HTML: {e}")
                        except:
                            pass
                except Exception as e:
                    print(f"[Extract] Error checking cache iframe: {e}")
            
            # If still no streams, wait a bit more and check again
            if not stream_urls:
                print(f"[Extract] Waiting additional 10 seconds for delayed stream loading...")
                # Hide Flash popups during final wait
                for i in range(2):
                    page.wait_for_timeout(5000)
                    hide_flash_popups()
                # Re-check network responses
                print(f"[Extract] Final check for streams...")
                
                # One last attempt - check all network requests that happened
                print(f"[Extract] Summary: No .m3u8 URLs found after all attempts")
                print(f"[Extract] This link may not have an active stream, or it loads differently")
            
            browser.close()
            
            # Try fallback links after browser is closed
            if not stream_urls and allow_fallback and fallback_links:
                print(f"[Extract] Trying {len(fallback_links)} alternative webplayer2.php link(s)...")
                for alt_link in fallback_links[:3]:
                    print(f"[Extract]   Trying alternative: {alt_link[:80]}...")
                    try:
                        alt_stream, alt_referer = extract_stream_with_playwright(alt_link, timeout=30000, max_popup_closes=10, allow_fallback=False)
                        if alt_stream:
                            print(f"[Extract]   ✓ Success with alternative link!")
                            stream_urls.append(alt_stream)
                            referer = alt_referer or referer
                            break
                    except Exception as e:
                        print(f"[Extract]   ✗ Alternative link failed: {e}")
                        continue
            
            # If still no streams, try converting webplayer.php to webplayer2.php
            if not stream_urls and allow_fallback and 'webplayer.php' in webplayer_url and 'webplayer2.php' not in webplayer_url:
                print(f"[Extract] Trying webplayer2.php version as fallback...")
                alt_url = webplayer_url.replace('webplayer.php', 'webplayer2.php')
                print(f"[Extract]   Trying: {alt_url[:80]}...")
                try:
                    alt_stream, alt_referer = extract_stream_with_playwright(alt_url, timeout=30000, max_popup_closes=10, allow_fallback=False)
                    if alt_stream:
                        print(f"[Extract]   ✓ Success with webplayer2.php version!")
                        stream_urls.append(alt_stream)
                        referer = alt_referer or referer
                except Exception as e:
                    print(f"[Extract]   ✗ webplayer2.php version failed: {e}")
            
    except PlaywrightTimeoutError as e:
        error_message = f"Timeout: {str(e)}"
        print(f"[Extract] ✗ Timeout error: {e}")
    except Exception as e:
        error_message = str(e)
        print(f"[Extract] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    if stream_urls:
        print(f"[Extract] ✓ Successfully extracted {len(stream_urls)} stream URL(s)")
        return stream_urls[0], referer or "https://exposestrat.com/"
    else:
        print(f"[Extract] ✗ Failed to extract stream URL")
        if error_message:
            print(f"[Extract]   Error: {error_message}")
        return None, None


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
    
    # Get URL from query parameter, or use default
    event_url = request.args.get('url', EVENT_URL)
    
    # Validate URL
    if not event_url or not event_url.startswith('http'):
        return jsonify({
            'success': False,
            'error': 'Invalid URL provided'
        }), 400
    
    # Extract links from the provided URL
    print(f"[API] Extracting player links from: {event_url}")
    player_links = extract_player_links(event_url)
    print(f"[API] Found {len(player_links)} player links")
    
    # Update global cache if using default URL
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
            print(f"[API] This could mean:")
            print(f"[API]   - The stream hasn't started yet")
            print(f"[API]   - The link is broken/invalid")
            print(f"[API]   - The stream requires additional authentication")
            print(f"[API]   - The page structure changed")
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
        
        # Rewrite URLs to go through proxy
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

