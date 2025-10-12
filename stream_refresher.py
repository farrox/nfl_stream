#!/usr/bin/env python3
"""
Stream URL Refresher
Automatically fetches fresh stream URLs to overcome expiring security tokens
"""

import re
import time
import requests
from datetime import datetime
from flask import Flask, redirect, jsonify, render_template_string
import threading

app = Flask(__name__)

# Configuration
MAIN_PAGE_URL = "https://streamsgate.live/hd/hd-6.php"
REFRESH_INTERVAL = 3600  # Refresh every hour (3600 seconds)
current_stream_url = None
last_refresh_time = None
stream_info = {}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto-Refreshing Stream Player</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
            font-size: 28px;
        }
        
        .info-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .info-item:last-child { border-bottom: none; }
        
        .info-label { font-weight: 600; opacity: 0.9; }
        .info-value { font-family: monospace; }
        
        #video-container {
            position: relative;
            width: 100%;
            background: #000;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 20px;
        }
        
        video {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        
        button {
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .btn-play { background: #28a745; color: white; }
        .btn-pause { background: #ffc107; color: #333; }
        .btn-reload { background: #17a2b8; color: white; }
        .btn-fullscreen { background: #6f42c1; color: white; }
        .btn-refresh { background: #dc3545; color: white; }
        
        #status {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .status-loading { background: #fff3cd; color: #856404; }
        .status-playing { background: #d4edda; color: #155724; }
        .status-error { background: #f8d7da; color: #721c24; }
        .status-paused { background: #d1ecf1; color: #0c5460; }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 Auto-Refreshing Stream Player</h1>
        
        <div class="info-box">
            <div class="info-item">
                <span class="info-label">Stream ID:</span>
                <span class="info-value">{{ stream_id }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Last Refresh:</span>
                <span class="info-value" id="last-refresh">{{ last_refresh }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Next Refresh:</span>
                <span class="info-value" id="next-refresh">{{ next_refresh }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Auto-Refresh:</span>
                <span class="info-value">✅ Enabled (every {{ refresh_interval }}s)</span>
            </div>
        </div>
        
        <div id="video-container">
            <video id="video" controls autoplay></video>
        </div>
        
        <div class="controls">
            <button class="btn-play" onclick="playVideo()">▶️ Play</button>
            <button class="btn-pause" onclick="pauseVideo()">⏸️ Pause</button>
            <button class="btn-reload" onclick="reloadStream()">🔄 Reload</button>
            <button class="btn-fullscreen" onclick="goFullscreen()">⛶ Fullscreen</button>
            <button class="btn-refresh" onclick="forceRefresh()">🔃 Force Refresh URL</button>
        </div>
        
        <div id="status" class="status-loading">Initializing player...</div>
    </div>

    <script>
        const video = document.getElementById('video');
        const status = document.getElementById('status');
        let hls;
        let currentStreamUrl = null;
        let refreshInterval = {{ refresh_interval }} * 1000;
        let checkInterval;

        function updateStatus(message, className) {
            status.textContent = message;
            status.className = className;
        }

        async function getCurrentStreamUrl() {
            try {
                // Use the proxied stream URL instead of direct URL
                return '/stream.m3u8';
            } catch (error) {
                console.error('Error fetching stream URL:', error);
                return null;
            }
        }

        async function updateStreamInfo() {
            try {
                const response = await fetch('/api/stream-info');
                const data = await response.json();
                document.getElementById('last-refresh').textContent = data.last_refresh;
                document.getElementById('next-refresh').textContent = data.next_refresh;
            } catch (error) {
                console.error('Error updating stream info:', error);
            }
        }

        async function checkForNewUrl() {
            const newUrl = await getCurrentStreamUrl();
            if (newUrl && newUrl !== currentStreamUrl) {
                console.log('New stream URL detected, updating player...');
                currentStreamUrl = newUrl;
                const wasPlaying = !video.paused;
                const currentTime = video.currentTime;
                
                await initPlayer();
                
                if (wasPlaying) {
                    setTimeout(() => {
                        video.currentTime = currentTime;
                        video.play();
                    }, 1000);
                }
            }
            await updateStreamInfo();
        }

        async function initPlayer() {
            if (!currentStreamUrl) {
                currentStreamUrl = await getCurrentStreamUrl();
            }

            if (!currentStreamUrl) {
                updateStatus('❌ Failed to get stream URL', 'status-error');
                return;
            }

            if (hls) {
                hls.destroy();
            }

            if (Hls.isSupported()) {
                hls = new Hls({
                    enableWorker: true,
                    lowLatencyMode: true,
                    backBufferLength: 90
                });
                
                hls.loadSource(currentStreamUrl);
                hls.attachMedia(video);
                
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    updateStatus('✅ Stream ready - Playing...', 'status-playing');
                    video.play().catch(e => {
                        updateStatus('⚠️ Click Play button to start', 'status-paused');
                    });
                });
                
                hls.on(Hls.Events.ERROR, function(event, data) {
                    if (data.fatal) {
                        switch(data.type) {
                            case Hls.ErrorTypes.NETWORK_ERROR:
                                updateStatus('❌ Network error - Refreshing URL...', 'status-error');
                                setTimeout(() => forceRefresh(), 2000);
                                break;
                            case Hls.ErrorTypes.MEDIA_ERROR:
                                updateStatus('⚠️ Media error - Recovering...', 'status-error');
                                hls.recoverMediaError();
                                break;
                            default:
                                updateStatus('❌ Fatal error - Refreshing...', 'status-error');
                                setTimeout(() => forceRefresh(), 2000);
                                break;
                        }
                    }
                });
                
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = currentStreamUrl;
                video.addEventListener('loadedmetadata', function() {
                    updateStatus('✅ Stream ready', 'status-playing');
                    video.play();
                });
            }

            video.addEventListener('playing', () => {
                updateStatus('▶️ Playing stream...', 'status-playing');
            });
            
            video.addEventListener('pause', () => {
                updateStatus('⏸️ Paused', 'status-paused');
            });
            
            video.addEventListener('waiting', () => {
                updateStatus('⏳ Buffering...', 'status-loading');
            });
        }

        function playVideo() {
            video.play();
        }

        function pauseVideo() {
            video.pause();
        }

        async function reloadStream() {
            updateStatus('🔄 Reloading stream...', 'status-loading');
            await initPlayer();
        }

        async function forceRefresh() {
            updateStatus('🔃 Fetching new stream URL...', 'status-loading pulse');
            try {
                const response = await fetch('/api/refresh');
                const data = await response.json();
                if (data.success) {
                    currentStreamUrl = data.url;
                    await initPlayer();
                    updateStatus('✅ Stream URL refreshed!', 'status-playing');
                } else {
                    updateStatus('❌ Failed to refresh URL', 'status-error');
                }
            } catch (error) {
                updateStatus('❌ Error refreshing URL', 'status-error');
            }
            await updateStreamInfo();
        }

        function goFullscreen() {
            const container = document.getElementById('video-container');
            if (container.requestFullscreen) {
                container.requestFullscreen();
            } else if (container.webkitRequestFullscreen) {
                container.webkitRequestFullscreen();
            }
        }

        // Initialize
        initPlayer();
        updateStreamInfo();

        // Check for new URL every 10 seconds
        checkInterval = setInterval(checkForNewUrl, 10000);
    </script>
</body>
</html>
"""


def extract_iframe_url(html_content):
    """Extract iframe URL from main page"""
    match = re.search(r'<iframe\s+src="([^"]+)"', html_content)
    if match:
        url = match.group(1)
        if url.startswith('//'):
            url = 'https:' + url
        return url
    return None


def extract_stream_url(iframe_content):
    """Extract stream URL from iframe content"""
    match = re.search(r'source:\s*"([^"]+\.m3u8[^"]*)"', iframe_content)
    if match:
        return match.group(1).replace('&amp;', '&')
    return None


def extract_stream_id(iframe_url):
    """Extract stream ID from iframe URL"""
    match = re.search(r'stream=([^&]+)', iframe_url)
    if match:
        return match.group(1)
    return "Unknown"


def fetch_fresh_stream_url():
    """Fetch a fresh stream URL with new security token"""
    global current_stream_url, last_refresh_time, stream_info
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching fresh stream URL...")
    
    try:
        # Step 1: Get main page
        print("→ Fetching main page...")
        response = requests.get(MAIN_PAGE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # Step 2: Extract iframe URL
        iframe_url = extract_iframe_url(response.text)
        if not iframe_url:
            print("✗ Failed to extract iframe URL")
            return None
        
        print(f"→ Found iframe: {iframe_url}")
        
        # Step 3: Fetch iframe content with referrer
        headers_with_referrer = HEADERS.copy()
        headers_with_referrer['Referer'] = MAIN_PAGE_URL
        
        print("→ Fetching iframe content...")
        iframe_response = requests.get(iframe_url, headers=headers_with_referrer, timeout=10)
        iframe_response.raise_for_status()
        
        # Step 4: Extract stream URL
        stream_url = extract_stream_url(iframe_response.text)
        if not stream_url:
            print("✗ Failed to extract stream URL")
            return None
        
        # Update global state
        current_stream_url = stream_url
        last_refresh_time = datetime.now()
        stream_info = {
            'url': stream_url,
            'stream_id': extract_stream_id(iframe_url),
            'last_refresh': last_refresh_time.strftime('%Y-%m-%d %H:%M:%S'),
            'iframe_url': iframe_url
        }
        
        print(f"✓ Stream URL updated successfully!")
        print(f"  URL: {stream_url[:80]}...")
        
        return stream_url
        
    except Exception as e:
        print(f"✗ Error fetching stream URL: {e}")
        return None


def auto_refresh_worker():
    """Background worker to automatically refresh stream URL"""
    while True:
        fetch_fresh_stream_url()
        print(f"→ Next refresh in {REFRESH_INTERVAL} seconds...")
        time.sleep(REFRESH_INTERVAL)


# Flask Routes
@app.route('/')
def index():
    """Serve the player page"""
    if not current_stream_url:
        fetch_fresh_stream_url()
    
    next_refresh = last_refresh_time.timestamp() + REFRESH_INTERVAL if last_refresh_time else time.time()
    next_refresh_str = datetime.fromtimestamp(next_refresh).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template_string(
        HTML_TEMPLATE,
        stream_id=stream_info.get('stream_id', 'Unknown'),
        last_refresh=stream_info.get('last_refresh', 'Never'),
        next_refresh=next_refresh_str,
        refresh_interval=REFRESH_INTERVAL
    )


@app.route('/api/stream-url')
def get_stream_url():
    """API endpoint to get current stream URL"""
    if not current_stream_url:
        fetch_fresh_stream_url()
    return jsonify({'url': current_stream_url})


@app.route('/api/stream-info')
def get_stream_info():
    """API endpoint to get stream information"""
    next_refresh = last_refresh_time.timestamp() + REFRESH_INTERVAL if last_refresh_time else time.time()
    next_refresh_str = datetime.fromtimestamp(next_refresh).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'stream_id': stream_info.get('stream_id', 'Unknown'),
        'last_refresh': stream_info.get('last_refresh', 'Never'),
        'next_refresh': next_refresh_str,
        'url': current_stream_url
    })


@app.route('/api/refresh')
def force_refresh():
    """API endpoint to force refresh the stream URL"""
    new_url = fetch_fresh_stream_url()
    return jsonify({
        'success': new_url is not None,
        'url': new_url
    })


@app.route('/stream.m3u8')
def stream_proxy():
    """Proxy the M3U8 stream with proper headers and rewrite URLs"""
    if not current_stream_url:
        fetch_fresh_stream_url()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://arizonaplay.club/',
            'Origin': 'https://arizonaplay.club'
        }
        response = requests.get(current_stream_url, headers=headers, timeout=10)
        
        # Parse and rewrite M3U8 content
        content = response.text
        base_url = current_stream_url.rsplit('/', 1)[0] + '/'
        
        # Rewrite relative URLs to go through our proxy
        lines = content.split('\n')
        rewritten_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # This is a segment URL
                if not line.startswith('http'):
                    # Relative URL - make it absolute and proxy it
                    segment_url = base_url + line
                else:
                    segment_url = line
                
                # Encode the URL and proxy it through our server
                import urllib.parse
                encoded_url = urllib.parse.quote(segment_url, safe='')
                line = f'/proxy/{encoded_url}'
            rewritten_lines.append(line)
        
        rewritten_content = '\n'.join(rewritten_lines)
        
        # Return the content with CORS headers
        from flask import Response
        return Response(
            rewritten_content,
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
def proxy_stream(url):
    """Proxy any stream segment with proper headers"""
    try:
        # Decode the URL
        import urllib.parse
        decoded_url = urllib.parse.unquote(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://arizonaplay.club/',
            'Origin': 'https://arizonaplay.club'
        }
        response = requests.get(decoded_url, headers=headers, timeout=10, stream=True)
        
        from flask import Response
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


def main():
    print("=" * 60)
    print("🎥 Auto-Refreshing Stream Player")
    print("=" * 60)
    print(f"Main page: {MAIN_PAGE_URL}")
    print(f"Auto-refresh interval: {REFRESH_INTERVAL} seconds")
    print()
    
    # Fetch initial stream URL
    fetch_fresh_stream_url()
    
    if not current_stream_url:
        print("\n✗ Failed to fetch initial stream URL. Exiting...")
        return
    
    # Start background refresh worker
    refresh_thread = threading.Thread(target=auto_refresh_worker, daemon=True)
    refresh_thread.start()
    
    print("\n" + "=" * 60)
    print("🌐 Server starting...")
    print("=" * 60)
    print("\n📺 Open in your browser:")
    print("   http://localhost:8080")
    print("\n🎬 Or use with VLC/mpv:")
    print("   vlc http://localhost:8080/stream.m3u8")
    print("   mpv http://localhost:8080/stream.m3u8")
    print("\n⌨️  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8080, debug=False)


if __name__ == '__main__':
    main()

