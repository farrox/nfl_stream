#!/usr/bin/env python3
"""
Flask server that extracts and serves streams from rojadirecta URLs.
"""
from flask import Flask, Response, render_template_string, request, jsonify
import requests
from extract_rojadirecta import extract_rojadirecta_stream
import time
import sys

app = Flask(__name__)

# Global variables to store current stream info
current_stream = {
    'url': None,
    'referer': None,
    'last_updated': 0,
    'rojadirecta_url': None
}

# Refresh interval (1 hour)
REFRESH_INTERVAL = 3600

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Rojadirecta Stream Player</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #000;
            color: #fff;
            font-family: Arial, sans-serif;
        }
        #videoContainer {
            max-width: 1280px;
            margin: 0 auto;
        }
        video {
            width: 100%;
            height: auto;
            background: #000;
        }
        .info {
            margin: 20px 0;
            padding: 15px;
            background: #222;
            border-radius: 5px;
        }
        .info h2 {
            margin-top: 0;
        }
        .status {
            color: #4CAF50;
            font-weight: bold;
        }
        .error {
            color: #f44336;
        }
        .url {
            word-break: break-all;
            font-size: 12px;
            color: #888;
        }
        button {
            background: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 16px;
            margin: 5px;
        }
        button:hover {
            background: #0b7dda;
        }
    </style>
</head>
<body>
    <div id="videoContainer">
        <h1>🏈 Rojadirecta Stream Player</h1>
        
        <div class="info">
            <h2>Stream Status</h2>
            <div id="status">Loading...</div>
            <div class="url" id="streamUrl"></div>
        </div>
        
        <video id="video" controls autoplay></video>
        
        <div class="info">
            <button onclick="refreshStream()">🔄 Refresh Stream</button>
            <button onclick="updateStreamInfo()">ℹ️ Update Info</button>
        </div>
    </div>

    <script>
        var video = document.getElementById('video');
        var hls;

        function updateStreamInfo() {
            fetch('/api/stream_info')
                .then(response => response.json())
                .then(data => {
                    var statusDiv = document.getElementById('status');
                    var urlDiv = document.getElementById('streamUrl');
                    
                    if (data.url) {
                        statusDiv.innerHTML = '<span class="status">✓ Stream Active</span>';
                        urlDiv.textContent = 'Stream URL: ' + data.url;
                    } else {
                        statusDiv.innerHTML = '<span class="error">✗ No stream available</span>';
                        urlDiv.textContent = '';
                    }
                })
                .catch(error => {
                    console.error('Error fetching stream info:', error);
                });
        }

        function loadStream() {
            if (Hls.isSupported()) {
                hls = new Hls({
                    xhrSetup: function(xhr, url) {
                        // Proxy will handle headers
                    }
                });
                
                hls.loadSource('/stream.m3u8');
                hls.attachMedia(video);
                
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    console.log('Stream loaded successfully');
                    updateStreamInfo();
                });
                
                hls.on(Hls.Events.ERROR, function(event, data) {
                    console.error('HLS error:', data);
                    if (data.fatal) {
                        switch(data.type) {
                            case Hls.ErrorTypes.NETWORK_ERROR:
                                console.log('Network error, trying to recover...');
                                hls.startLoad();
                                break;
                            case Hls.ErrorTypes.MEDIA_ERROR:
                                console.log('Media error, trying to recover...');
                                hls.recoverMediaError();
                                break;
                            default:
                                console.log('Fatal error, destroying player...');
                                hls.destroy();
                                break;
                        }
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = '/stream.m3u8';
            }
        }

        function refreshStream() {
            document.getElementById('status').innerHTML = 'Refreshing stream...';
            fetch('/api/refresh')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (hls) {
                            hls.destroy();
                        }
                        setTimeout(loadStream, 1000);
                    } else {
                        alert('Failed to refresh stream: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    alert('Error refreshing stream: ' + error);
                });
        }

        // Load stream on page load
        loadStream();
        
        // Update info periodically
        setInterval(updateStreamInfo, 10000);
    </script>
</body>
</html>
"""

def fetch_stream_content(url, referer):
    """Fetch content from stream URL with proper headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': referer,
        'Origin': 'https://www.cdn291.info',
        'Accept': '*/*'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        return response
    except Exception as e:
        print(f"Error fetching stream content: {e}")
        return None

def update_stream():
    """Extract fresh stream URL from rojadirecta"""
    global current_stream
    
    if not current_stream['rojadirecta_url']:
        print("No rojadirecta URL configured")
        return False
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Extracting stream from rojadirecta...")
    
    stream_info = extract_rojadirecta_stream(current_stream['rojadirecta_url'])
    
    if stream_info and stream_info['url']:
        current_stream['url'] = stream_info['url']
        current_stream['referer'] = stream_info['referer']
        current_stream['last_updated'] = time.time()
        print(f"✓ Stream URL updated: {stream_info['url']}")
        return True
    else:
        print("✗ Failed to extract stream URL")
        return False

@app.route('/')
def index():
    """Serve the video player page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/stream.m3u8')
def stream_m3u8():
    """Proxy the m3u8 playlist"""
    # Check if stream needs refresh
    if time.time() - current_stream['last_updated'] > REFRESH_INTERVAL:
        update_stream()
    
    if not current_stream['url']:
        return "Stream not available", 503
    
    response = fetch_stream_content(current_stream['url'], current_stream['referer'])
    
    if response and response.status_code == 200:
        content = response.text
        # Modify relative URLs in playlist to be proxied through our server
        if current_stream['url']:
            base_url = current_stream['url'].rsplit('/', 1)[0]
            # Replace relative URLs with absolute ones
            lines = content.split('\n')
            modified_lines = []
            for line in lines:
                if line and not line.startswith('#'):
                    if not line.startswith('http'):
                        line = f"{base_url}/{line}"
                    # Proxy through our server
                    line = f"/proxy?url={line}"
                modified_lines.append(line)
            content = '\n'.join(modified_lines)
        
        return Response(content, mimetype='application/vnd.apple.mpegurl')
    else:
        return "Stream not available", 503

@app.route('/proxy')
def proxy():
    """Proxy video segments and playlists"""
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    
    response = fetch_stream_content(url, current_stream['referer'])
    
    if response and response.status_code == 200:
        # Determine content type
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        
        if url.endswith('.m3u8'):
            # Process nested playlists
            content = response.text
            base_url = url.rsplit('/', 1)[0]
            lines = content.split('\n')
            modified_lines = []
            for line in lines:
                if line and not line.startswith('#'):
                    if not line.startswith('http'):
                        line = f"{base_url}/{line}"
                    line = f"/proxy?url={line}"
                modified_lines.append(line)
            content = '\n'.join(modified_lines)
            return Response(content, mimetype='application/vnd.apple.mpegurl')
        else:
            # Stream video segments
            return Response(response.iter_content(chunk_size=4096), mimetype=content_type)
    else:
        return "Content not available", 503

@app.route('/api/stream_info')
def stream_info():
    """Return current stream information"""
    return jsonify({
        'url': current_stream['url'],
        'referer': current_stream['referer'],
        'last_updated': current_stream['last_updated'],
        'rojadirecta_url': current_stream['rojadirecta_url']
    })

@app.route('/api/refresh')
def refresh():
    """Force refresh the stream URL"""
    success = update_stream()
    return jsonify({
        'success': success,
        'url': current_stream['url'] if success else None
    })

def main():
    if len(sys.argv) < 2:
        print("Usage: python rojadirecta_server.py <rojadirecta_url>")
        print("\nExample:")
        print("  python rojadirecta_server.py 'https://rojadirectame.eu/football/event-url'")
        sys.exit(1)
    
    # Set rojadirecta URL
    current_stream['rojadirecta_url'] = sys.argv[1]
    
    # Extract initial stream
    print("="*60)
    print("🎥 Rojadirecta Stream Server")
    print("="*60)
    print(f"Rojadirecta URL: {current_stream['rojadirecta_url']}")
    print()
    
    if update_stream():
        print("\n" + "="*60)
        print("🌐 Starting server...")
        print("="*60)
        print()
        print("📺 Open in your browser:")
        print("   http://localhost:8080")
        print()
        print("⌨️  Press Ctrl+C to stop")
        print("="*60)
        print()
        
        app.run(host='0.0.0.0', port=8080, debug=False)
    else:
        print("\n✗ Failed to extract initial stream. Server not started.")
        sys.exit(1)

if __name__ == '__main__':
    main()

