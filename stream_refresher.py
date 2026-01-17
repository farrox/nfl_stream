#!/usr/bin/env python3
"""
Stream URL Refresher
Automatically fetches fresh stream URLs to overcome expiring security tokens
"""

import re
import time
import requests
from datetime import datetime, date
from flask import Flask, redirect, jsonify, render_template_string, request
import threading
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sqlite3
import os

# Try to import Playwright for JavaScript-based extraction
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Configuration
MAIN_PAGE_URL = "https://streamsgate.live/hd/hd-6.php"
REFRESH_INTERVAL = 3600  # Refresh every hour (3600 seconds)
current_stream_url = None
last_refresh_time = None
stream_info = {}
available_channels = []  # Store all available channels
current_channel_index = 0  # Track which channel we're using

# Database configuration
DB_FILE = 'streams.db'
TRACKED_GAMES = ['patriots', 'falcons']  # Games to track in database
last_run_date = None  # Track last run date to detect new day

# Stream sources to search
STREAM_SOURCES = [
    {
        'name': 'Rojadirecta',
        'base_url': 'https://rojadirectame.eu',
        'search_url': 'https://rojadirectame.eu/football',
        'enabled': True,
        'priority': 0  # Try first
    },
    {
        'name': 'LiveTV.sx',
        'base_url': 'https://livetv.sx',
        'search_url': 'https://livetv.sx/enx/',
        'enabled': True,
        'priority': 1
    },
    {
        'name': 'LiveTV 872',
        'base_url': 'https://livetv872.me',
        'search_url': 'https://livetv872.me/enx/',
        'enabled': True,
        'priority': 1.5  # Alternative to livetv.sx
    },
    {
        'name': 'StreamEast',
        'base_url': 'https://streameast.app',
        'search_patterns': ['patriots', 'nfl', 'football'],
        'enabled': True,
        'priority': 2
    },
    {
        'name': 'StreamsGate',
        'base_url': 'https://streamsgate.live',
        'search_url': 'https://streamsgate.live',
        'enabled': True,
        'priority': 3
    },
    {
        'name': 'CrackStreams',
        'base_url': 'https://crackstreams.biz',
        'enabled': True,
        'priority': 4
    }
]

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
        
        .main-wrapper {
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
            gap: 20px;
        }
        
        .sidebar {
            width: 300px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-height: 90vh;
            overflow-y: auto;
        }
        
        .sidebar h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .channel-item {
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border-left: 3px solid #667eea;
        }
        
        .channel-item:hover {
            transform: translateX(5px);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
            background: #f0f4ff;
        }
        
        .channel-item.active {
            background: #667eea;
            color: white;
        }
        
        .channel-name {
            font-weight: 600;
            font-size: 14px;
        }
        
        .channel-source {
            font-size: 11px;
            opacity: 0.7;
            margin-top: 4px;
        }
        
        .container {
            flex: 1;
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
        .btn-next-channel { background: #fd7e14; color: white; }
        
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
        
        /* Manual Link Section Styles */
        .manual-link-section {
            margin-bottom: 20px;
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 15px;
        }
        
        .manual-link-section h3 {
            margin: 0 0 10px 0;
            color: #856404;
            font-size: 14px;
            font-weight: 600;
        }
        
        .manual-link-input {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .manual-link-input input {
            flex: 1;
            padding: 10px;
            border: 2px solid #ffc107;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .manual-link-input input:focus {
            outline: none;
            border-color: #ff9800;
        }
        
        .btn-add-manual {
            padding: 10px 20px;
            background: #ffc107;
            color: #333;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-add-manual:hover {
            background: #ff9800;
            transform: translateY(-2px);
        }
        
        .manual-link-item {
            background: white;
            padding: 12px;
            margin-top: 10px;
            border-radius: 6px;
            border-left: 4px solid #ffc107;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .manual-link-item:hover {
            transform: translateX(5px);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        }
        
        .manual-link-label {
            font-weight: 600;
            color: #856404;
            font-size: 12px;
            margin-bottom: 5px;
        }
        
        .manual-link-url {
            font-size: 11px;
            color: #666;
            font-family: monospace;
            word-break: break-all;
        }
        
        /* Search Section Styles */
        .search-section {
            margin-bottom: 20px;
        }
        
        .search-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        #search-input {
            flex: 1;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            transition: border-color 0.3s;
        }
        
        #search-input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn-search {
            padding: 12px 30px;
            background: #667eea;
            color: white;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-search:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }
        
        .search-results {
            display: none;
            max-height: 400px;
            overflow-y: auto;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
        }
        
        .search-results.active {
            display: block;
        }
        
        .search-result-item {
            background: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border-left: 4px solid #667eea;
        }
        
        .search-result-item:hover {
            transform: translateX(5px);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        }
        
        .search-result-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .search-result-meta {
            font-size: 12px;
            color: #666;
        }
        
        .search-result-source {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-right: 10px;
        }
        
        .search-loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .search-empty {
            text-align: center;
            padding: 20px;
            color: #999;
        }
        
        .channel-info {
            text-align: center;
            padding: 12px;
            margin-top: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        
        /* Add Good Link Section */
        .add-link-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #667eea;
        }
        
        .add-link-toggle {
            background: #667eea;
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            transition: all 0.3s;
            margin-bottom: 10px;
        }
        
        .add-link-toggle:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        
        .add-link-form {
            display: none;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
        }
        
        .add-link-form.active {
            display: block;
        }
        
        .add-link-form textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            font-family: monospace;
            resize: vertical;
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        
        .add-link-form textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .add-link-form input {
            width: 100%;
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        
        .add-link-form input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn-add-link {
            width: 100%;
            padding: 10px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-add-link:hover {
            background: #218838;
            transform: translateY(-2px);
        }
        
        .add-link-message {
            margin-top: 10px;
            padding: 8px;
            border-radius: 6px;
            font-size: 12px;
            text-align: center;
            display: none;
        }
        
        .add-link-message.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        
        .add-link-message.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        
        /* Links Management Section */
        .links-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #667eea;
        }
        
        .links-toggle {
            background: #28a745;
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            transition: all 0.3s;
            margin-bottom: 10px;
        }
        
        .links-toggle:hover {
            background: #218838;
            transform: translateY(-2px);
        }
        
        .links-list {
            display: none;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .links-list.active {
            display: block;
        }
        
        .link-item {
            background: white;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 6px;
            border-left: 3px solid #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .link-item.wrong-game {
            opacity: 0.6;
            border-left-color: #dc3545;
            background: #fff5f5;
        }
        
        .link-item.good-status {
            border-left-color: #28a745;
        }
        
        .link-item.bad-status {
            border-left-color: #ffc107;
        }
        
        .link-checkbox {
            width: 20px;
            height: 20px;
            cursor: pointer;
            flex-shrink: 0;
        }
        
        .link-details {
            flex: 1;
            min-width: 0;
        }
        
        .link-url {
            font-size: 11px;
            font-family: monospace;
            color: #666;
            word-break: break-all;
            margin-bottom: 4px;
        }
        
        .link-meta {
            font-size: 10px;
            color: #999;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .link-status-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .link-status-badge.good {
            background: #d4edda;
            color: #155724;
        }
        
        .link-status-badge.bad {
            background: #fff3cd;
            color: #856404;
        }
        
        .links-empty {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 13px;
        }
        
        .links-loading {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <!-- Sidebar for available channels -->
        <div class="sidebar">
            <h3>🏈 Available Channels</h3>
            <div id="channels-list">
                <div style="padding: 20px; text-align: center; color: #666;">
                    Loading Patriots game...
                </div>
            </div>
            
            <!-- Add Good Link Section -->
            <div class="add-link-section">
                <div class="add-link-toggle" onclick="toggleAddLinkForm()">
                    ➕ Add Good Link
                </div>
                <div id="add-link-form" class="add-link-form">
                    <label style="display: block; margin-bottom: 5px; font-size: 12px; font-weight: 600; color: #333;">
                        Stream URL (M3U8):
                    </label>
                    <textarea id="link-url-input" placeholder="Paste stream URL here (e.g., https://example.com/stream.m3u8)" rows="3"></textarea>
                    
                    <label style="display: block; margin-bottom: 5px; font-size: 12px; font-weight: 600; color: #333;">
                        Channel Name (optional):
                    </label>
                    <input type="text" id="link-name-input" placeholder="e.g., HD Stream, Backup Link" />
                    
                    <label style="display: block; margin-bottom: 5px; font-size: 12px; font-weight: 600; color: #333;">
                        Game Title (optional):
                    </label>
                    <input type="text" id="link-game-input" placeholder="e.g., Patriots vs Falcons" />
                    
                    <button class="btn-add-link" onclick="addGoodLink()">
                        ✅ Save as Good Link
                    </button>
                    <div id="add-link-message" class="add-link-message"></div>
                </div>
            </div>
            
            <!-- Manage Links Section -->
            <div class="links-section">
                <div class="links-toggle" onclick="toggleLinksList()">
                    📋 Manage Links
                </div>
                <div id="links-list" class="links-list">
                    <div class="links-empty">Load a game to see links</div>
                </div>
            </div>
        </div>
        
        <div class="container">
            <h1>🎥 Auto-Refreshing Stream Player</h1>
            
            <!-- Manual Link Addition Section -->
            <div class="manual-link-section">
                <h3>🔗 Add Manual Link (Appears First in Results)</h3>
                <div class="manual-link-input">
                    <input type="text" id="manual-link-url" placeholder="Paste event URL here (e.g., https://livetv.sx/enx/eventinfo/314788282__/)" />
                    <input type="text" id="manual-link-title" placeholder="Game title (optional)" />
                    <button class="btn-add-manual" onclick="addManualLink()">➕ Add</button>
                </div>
                <div id="manual-links-list"></div>
            </div>
            
            <!-- Search Bar -->
            <div class="search-section">
                <div class="search-bar">
                    <input type="text" id="search-input" placeholder="Search for games (e.g., barcelona madrid, patriots browns)..." value="patriots" />
                    <button class="btn-search" onclick="searchGames()">🔍 Search</button>
                </div>
                <div id="search-results" class="search-results"></div>
            </div>
        
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
            <button class="btn-next-channel" onclick="nextChannel()" id="next-channel-btn" style="display: none;">⏭️ Next Channel</button>
            <button class="btn-refresh" onclick="forceRefresh()">🔃 Force Refresh URL</button>
        </div>
        
        <div id="channel-info" class="channel-info" style="display: none;"></div>
        
        <div id="status" class="status-loading">Initializing player...</div>
        </div>
    </div>

    <script>
        const video = document.getElementById('video');
        const status = document.getElementById('status');
        let hls;
        let currentStreamUrl = null;
        let refreshInterval = {{ refresh_interval }} * 1000;
        let checkInterval;
        let allChannels = [];
        let currentChannelIndex = 0;

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

        // Update sidebar with all available channels
        function updateChannelsSidebar(channels) {
            const channelsList = document.getElementById('channels-list');
            if (!channels || channels.length === 0) {
                channelsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No channels available</div>';
                return;
            }
            
            let html = '';
            channels.forEach((channel, index) => {
                const isActive = index === currentChannelIndex;
                html += `
                    <div class="channel-item ${isActive ? 'active' : ''}" onclick="switchToChannel(${index})">
                        <div class="channel-name">${channel.name}</div>
                        <div class="channel-source">${channel.source || 'Unknown'}</div>
                    </div>
                `;
            });
            channelsList.innerHTML = html;
        }
        
        // Switch to a specific channel/game
        async function switchToChannel(index) {
            if (index < 0 || index >= allChannels.length) return;
            
            const channel = allChannels[index];
            currentChannelIndex = index;
            updateStatus(`⏭️ Loading ${channel.name.substring(0, 30)}...`, 'status-loading pulse');
            
            try {
                // If it's a full game, load it
                if (channel.isGame) {
                    const loadResponse = await fetch(`/api/load-stream?url=${encodeURIComponent(channel.url)}&title=${encodeURIComponent(channel.name)}`);
                    const loadData = await loadResponse.json();
                    
                    if (loadData.success) {
                        currentStreamUrl = loadData.proxy_url;
                        await initPlayer();
                        updateStatus(`▶️ Playing: ${channel.name.substring(0, 40)}...`, 'status-playing');
                        updateChannelsSidebar(allChannels);
                    } else {
                        updateStatus('❌ Failed to load - try another link', 'status-error');
                        console.error('Load error:', loadData.error);
                    }
                } else {
                    // It's a channel from same game, use next-channel API
                    const response = await fetch('/api/next-channel');
                    const data = await response.json();
                    
                    if (data.success) {
                        currentStreamUrl = data.proxy_url;
                        await initPlayer();
                        updateStatus(`✅ ${data.channel_name}`, 'status-playing');
                        updateChannelsSidebar(allChannels);
                    } else {
                        updateStatus('❌ Failed to switch channel', 'status-error');
                    }
                }
            } catch (error) {
                console.error('Channel switch error:', error);
                updateStatus('❌ Error switching channel', 'status-error');
            }
        }
        
        // Auto-load Patriots game on startup
        async function autoLoadPatriots() {
            updateStatus('🏈 Searching for Patriots games...', 'status-loading pulse');
            const channelsList = document.getElementById('channels-list');
            channelsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">🔍 Searching for Patriots games...</div>';
            
            try {
                // First search for Patriots
                const searchResponse = await fetch('/api/search?q=patriots');
                const searchData = await searchResponse.json();
                
                if (searchData.success && searchData.results.length > 0) {
                    // Store ALL games as channels
                    allChannels = searchData.results.map((game, index) => ({
                        name: game.title,
                        source: game.source,
                        url: game.url,
                        isGame: true  // Mark as full game, not just a channel
                    }));
                    
                    // Display all games in sidebar
                    updateChannelsSidebar(allChannels);
                    
                    // Load the first game automatically
                    const patriotsGame = searchData.results[0];
                    updateStatus(`📡 Loading ${patriotsGame.title}...`, 'status-loading pulse');
                    
                    const loadResponse = await fetch(`/api/load-stream?url=${encodeURIComponent(patriotsGame.url)}&title=${encodeURIComponent(patriotsGame.title)}`);
                    const loadData = await loadResponse.json();
                    
                    if (loadData.success) {
                        currentChannelIndex = 0;
                        currentStreamUrl = loadData.proxy_url;
                        await initPlayer();
                        updateStatus(`▶️ Playing: ${patriotsGame.title.substring(0, 40)}...`, 'status-playing');
                        
                        // Highlight the active channel
                        updateChannelsSidebar(allChannels);
                        
                        // Refresh links list if open
                        if (document.getElementById('links-list').classList.contains('active')) {
                            loadLinksList();
                        }
                    } else {
                        updateStatus('❌ Failed to load stream - try another link', 'status-error');
                        console.error('Load error:', loadData.error);
                    }
                } else {
                    updateStatus('⚠️ No Patriots game found - use search', 'status-paused');
                    channelsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No Patriots game found.<br>Use the search bar above.</div>';
                }
            } catch (error) {
                console.error('Auto-load error:', error);
                updateStatus('❌ Error auto-loading game', 'status-error');
                channelsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">Error loading game.<br>Use search to find one.</div>';
            }
        }

        // Initialize
        updateStreamInfo();

        // Check for new URL every 10 seconds
        checkInterval = setInterval(checkForNewUrl, 10000);
        
        // Auto-load Patriots game on page load
        autoLoadPatriots();
        
        // Manual Links Management
        let manualLinks = JSON.parse(localStorage.getItem('manualLinks') || '[]');
        
        function saveManualLinks() {
            localStorage.setItem('manualLinks', JSON.stringify(manualLinks));
        }
        
        function displayManualLinks() {
            const manualLinksList = document.getElementById('manual-links-list');
            if (manualLinks.length === 0) {
                manualLinksList.innerHTML = '';
                return;
            }
            
            let html = '';
            manualLinks.forEach((link, index) => {
                const shortUrl = link.url.length > 60 ? link.url.substring(0, 60) + '...' : link.url;
                html += `
                    <div class="manual-link-item" onclick="loadGame('${link.url.replace(/'/g, "\\'")}', '${link.title.replace(/'/g, "\\'")}')">
                        <div class="manual-link-label">${link.title || 'Manual Link'}</div>
                        <div class="manual-link-url">${shortUrl}</div>
                        <button onclick="event.stopPropagation(); removeManualLink(${index})" style="margin-top: 5px; padding: 4px 8px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px;">Remove</button>
                    </div>
                `;
            });
            manualLinksList.innerHTML = html;
        }
        
        function addManualLink() {
            const urlInput = document.getElementById('manual-link-url');
            const titleInput = document.getElementById('manual-link-title');
            const url = urlInput.value.trim();
            const title = titleInput.value.trim() || 'Manual Link';
            
            if (!url) {
                alert('Please enter a URL');
                return;
            }
            
            // Validate URL
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                alert('URL must start with http:// or https://');
                return;
            }
            
            // Check if already exists
            if (manualLinks.some(link => link.url === url)) {
                alert('This link is already added');
                return;
            }
            
            // Add to manual links
            manualLinks.push({ url: url, title: title });
            saveManualLinks();
            displayManualLinks();
            
            // Clear inputs
            urlInput.value = '';
            titleInput.value = '';
            
            // If search results are visible, refresh them to show manual link at top
            const searchResults = document.getElementById('search-results');
            if (searchResults.classList.contains('active')) {
                const searchInput = document.getElementById('search-input');
                if (searchInput.value.trim()) {
                    searchGames();
                }
            }
        }
        
        function removeManualLink(index) {
            if (confirm('Remove this manual link?')) {
                manualLinks.splice(index, 1);
                saveManualLinks();
                displayManualLinks();
                
                // Refresh search results if visible
                const searchResults = document.getElementById('search-results');
                if (searchResults.classList.contains('active')) {
                    const searchInput = document.getElementById('search-input');
                    if (searchInput.value.trim()) {
                        searchGames();
                    }
                }
            }
        }
        
        // Allow Enter key in manual link inputs
        document.getElementById('manual-link-url').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addManualLink();
            }
        });
        document.getElementById('manual-link-title').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addManualLink();
            }
        });
        
        // Initialize manual links display
        displayManualLinks();
        
        // Search functionality
        async function searchGames() {
            const searchInput = document.getElementById('search-input');
            const searchResults = document.getElementById('search-results');
            const query = searchInput.value.trim();
            
            if (!query) {
                alert('Please enter search keywords');
                return;
            }
            
            // Show loading state
            searchResults.innerHTML = '<div class="search-loading">🔍 Searching for games...</div>';
            searchResults.classList.add('active');
            
            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.success && data.results.length > 0) {
                    // Add manual links at the TOP of results
                    const allResults = [];
                    
                    // First, add manual links
                    manualLinks.forEach(link => {
                        allResults.push({
                            title: link.title,
                            url: link.url,
                            source: 'Manual Link',
                            isManual: true
                        });
                    });
                    
                    // Then add search results
                    allResults.push(...data.results);
                    
                    // Update sidebar with all games (including manual links)
                    allChannels = allResults.map((game, index) => ({
                        name: game.title,
                        source: game.source,
                        url: game.url,
                        isGame: true
                    }));
                    updateChannelsSidebar(allChannels);
                    
                    // Display results in search area
                    let html = `<div style="margin-bottom: 10px; font-weight: 600; color: #667eea;">Found ${data.count} game(s)${manualLinks.length > 0 ? ` + ${manualLinks.length} manual link(s)` : ''} - Click sidebar to play!</div>`;
                    
                    allResults.forEach(game => {
                        const isManual = game.isManual || false;
                        const isLive = game.is_live || false;
                        const score = game.score || null;
                        const borderColor = isManual ? '#ffc107' : (isLive ? '#e74c3c' : '#667eea');
                        const liveIndicator = isLive ? '<span style="background: #e74c3c; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-right: 8px;">🔴 LIVE</span>' : '';
                        const scoreDisplay = score ? `<span style="color: #e74c3c; font-weight: bold; margin-left: 8px;">${score}</span>` : '';
                        html += `
                            <div class="search-result-item" onclick="loadGame('${game.url.replace(/'/g, "\\'")}', '${game.title.replace(/'/g, "\\'")}')" style="border-left-color: ${borderColor};">
                                <div class="search-result-title">${isManual ? '🔗 ' : ''}${liveIndicator}${game.title}${scoreDisplay}</div>
                                <div class="search-result-meta">
                                    <span class="search-result-source" style="background: ${isManual ? '#ffc107' : (isLive ? '#e74c3c' : '#667eea')}; color: ${isManual ? '#333' : 'white'};">${game.source}</span>
                                    ${game.time ? `<span>⏰ ${game.time}</span>` : ''}
                                </div>
                            </div>
                        `;
                    });
                    
                    searchResults.innerHTML = html;
                } else {
                    // Even if no search results, show manual links if they exist
                    if (manualLinks.length > 0) {
                        const allResults = manualLinks.map(link => ({
                            title: link.title,
                            url: link.url,
                            source: 'Manual Link',
                            isManual: true
                        }));
                        
                        allChannels = allResults.map((game, index) => ({
                            name: game.title,
                            source: game.source,
                            url: game.url,
                            isGame: true
                        }));
                        updateChannelsSidebar(allChannels);
                        
                        let html = `<div style="margin-bottom: 10px; font-weight: 600; color: #667eea;">No search results, but ${manualLinks.length} manual link(s) available:</div>`;
                        allResults.forEach(game => {
                            html += `
                                <div class="search-result-item" onclick="loadGame('${game.url.replace(/'/g, "\\'")}', '${game.title.replace(/'/g, "\\'")}')" style="border-left-color: #ffc107;">
                                    <div class="search-result-title">🔗 ${game.title}</div>
                                    <div class="search-result-meta">
                                        <span class="search-result-source" style="background: #ffc107; color: #333;">${game.source}</span>
                                    </div>
                                </div>
                            `;
                        });
                        searchResults.innerHTML = html;
                    } else {
                        searchResults.innerHTML = '<div class="search-empty">😔 No games found. Try different keywords or add a manual link above.</div>';
                        allChannels = [];
                        updateChannelsSidebar(allChannels);
                    }
                }
            } catch (error) {
                console.error('Search error:', error);
                searchResults.innerHTML = '<div class="search-empty">❌ Search failed. Please try again.</div>';
            }
        }
        
        async function loadGame(gameUrl, gameTitle) {
            updateStatus('🔄 Loading stream from: ' + gameTitle.substring(0, 40), 'status-loading pulse');
            
            // Hide search results
            const searchResults = document.getElementById('search-results');
            searchResults.classList.remove('active');
            
            try {
                const response = await fetch(`/api/load-stream?url=${encodeURIComponent(gameUrl)}&title=${encodeURIComponent(gameTitle)}`);
                const data = await response.json();
                
                if (data.success) {
                    updateStatus('✅ Stream loaded! Starting playback...', 'status-playing');
                    
                    // Update stream info
                    document.getElementById('last-refresh').textContent = 'Just now';
                    
                    // Keep existing sidebar channels, just highlight the playing one
                    // Find the index of this game in allChannels
                    const gameIndex = allChannels.findIndex(ch => ch.url === gameUrl);
                    if (gameIndex >= 0) {
                        currentChannelIndex = gameIndex;
                    }
                    
                    updateChannelsSidebar(allChannels);
                    
                    // Refresh links list if open
                    if (document.getElementById('links-list').classList.contains('active')) {
                        loadLinksList();
                    }
                    
                    // Show channel info if multiple channels available
                    if (data.total_channels > 1) {
                        const channelInfo = document.getElementById('channel-info');
                        channelInfo.textContent = `📺 ${data.channel_name} (Channel ${data.current_channel}/${data.total_channels}) - Click "Next Channel" or sidebar`;
                        channelInfo.style.display = 'block';
                        
                        // Show next channel button
                        document.getElementById('next-channel-btn').style.display = 'inline-block';
                    } else {
                        document.getElementById('channel-info').style.display = 'none';
                        document.getElementById('next-channel-btn').style.display = 'none';
                    }
                    
                    // Reload player with new stream
                    currentStreamUrl = data.proxy_url;
                    await initPlayer();
                    
                    updateStatus('▶️ Playing: ' + gameTitle + ' (' + data.channel_name + ')', 'status-playing');
                } else {
                    updateStatus('❌ Failed to load stream: ' + (data.error || 'Unknown error'), 'status-error');
                    document.getElementById('channel-info').style.display = 'none';
                    document.getElementById('next-channel-btn').style.display = 'none';
                }
            } catch (error) {
                console.error('Load error:', error);
                updateStatus('❌ Error loading stream', 'status-error');
                document.getElementById('channel-info').style.display = 'none';
                document.getElementById('next-channel-btn').style.display = 'none';
            }
        }
        
        async function nextChannel() {
            updateStatus('⏭️ Switching to next channel...', 'status-loading pulse');
            
            try {
                const response = await fetch('/api/next-channel');
                const data = await response.json();
                
                if (data.success) {
                    // Update channel index
                    currentChannelIndex = (currentChannelIndex + 1) % allChannels.length;
                    
                    // Update sidebar
                    updateChannelsSidebar(allChannels);
                    
                    // Update channel info
                    const channelInfo = document.getElementById('channel-info');
                    channelInfo.textContent = `📺 ${data.channel_name} (Channel ${data.current_channel}/${data.total_channels}) - Click "Next Channel" or sidebar`;
                    
                    // Update stream info
                    document.getElementById('last-refresh').textContent = 'Just now';
                    
                    // Reload player with new stream
                    const wasPlaying = !video.paused;
                    currentStreamUrl = data.proxy_url;
                    await initPlayer();
                    
                    if (wasPlaying) {
                        setTimeout(() => video.play(), 500);
                    }
                    
                    updateStatus('✅ Switched to ' + data.channel_name, 'status-playing');
                } else {
                    updateStatus('❌ Failed to switch channel: ' + (data.error || 'Unknown error'), 'status-error');
                }
            } catch (error) {
                console.error('Channel switch error:', error);
                updateStatus('❌ Error switching channel', 'status-error');
            }
        }
        
        // Allow Enter key to search
        document.getElementById('search-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchGames();
            }
        });
        
        // Add Good Link Functions
        function toggleAddLinkForm() {
            const form = document.getElementById('add-link-form');
            form.classList.toggle('active');
        }
        
        async function addGoodLink() {
            const streamUrl = document.getElementById('link-url-input').value.trim();
            const channelName = document.getElementById('link-name-input').value.trim() || 'Manually Added';
            const gameTitle = document.getElementById('link-game-input').value.trim();
            const messageDiv = document.getElementById('add-link-message');
            
            if (!streamUrl) {
                messageDiv.textContent = 'Please enter a stream URL';
                messageDiv.className = 'add-link-message error';
                return;
            }
            
            // Validate URL
            if (!streamUrl.startsWith('http://') && !streamUrl.startsWith('https://')) {
                messageDiv.textContent = 'URL must start with http:// or https://';
                messageDiv.className = 'add-link-message error';
                return;
            }
            
            // Get current game URL if available
            const currentGameUrl = allChannels.length > 0 && allChannels[currentChannelIndex] ? 
                allChannels[currentChannelIndex].url : '';
            
            messageDiv.textContent = 'Adding link...';
            messageDiv.className = 'add-link-message';
            
            try {
                const response = await fetch('/api/add-good-link', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        stream_url: streamUrl,
                        channel_name: channelName,
                        game_title: gameTitle,
                        game_url: currentGameUrl
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    messageDiv.textContent = '✅ Link added as good link!';
                    messageDiv.className = 'add-link-message success';
                    
                    // Clear form
                    document.getElementById('link-url-input').value = '';
                    document.getElementById('link-name-input').value = '';
                    document.getElementById('link-game-input').value = '';
                    
                    // Hide form after 2 seconds
                    setTimeout(() => {
                        messageDiv.className = 'add-link-message';
                        document.getElementById('add-link-form').classList.remove('active');
                    }, 2000);
                    
                    // Refresh links list if open
                    if (document.getElementById('links-list').classList.contains('active')) {
                        loadLinksList();
                    }
                } else {
                    messageDiv.textContent = '❌ Error: ' + (data.error || 'Unknown error');
                    messageDiv.className = 'add-link-message error';
                }
            } catch (error) {
                messageDiv.textContent = '❌ Error adding link: ' + error.message;
                messageDiv.className = 'add-link-message error';
            }
        }
        
        // Links Management Functions
        function toggleLinksList() {
            const list = document.getElementById('links-list');
            list.classList.toggle('active');
            if (list.classList.contains('active')) {
                loadLinksList();
            }
        }
        
        async function loadLinksList() {
            const linksList = document.getElementById('links-list');
            linksList.innerHTML = '<div class="links-loading">Loading links...</div>';
            
            try {
                // Get current game URL
                const currentGameUrl = allChannels.length > 0 && allChannels[currentChannelIndex] ? 
                    allChannels[currentChannelIndex].url : '';
                
                if (!currentGameUrl) {
                    linksList.innerHTML = '<div class="links-empty">Please load a game first</div>';
                    return;
                }
                
                const response = await fetch(`/api/links?game_url=${encodeURIComponent(currentGameUrl)}&include_wrong=true`);
                const data = await response.json();
                
                if (data.success && data.links.length > 0) {
                    let html = '';
                    data.links.forEach(link => {
                        const wrongGameClass = link.wrong_game ? 'wrong-game' : '';
                        const statusClass = link.status === 'good' ? 'good-status' : 'bad-status';
                        const shortUrl = link.stream_url.length > 60 ? link.stream_url.substring(0, 60) + '...' : link.stream_url;
                        
                        html += `
                            <div class="link-item ${wrongGameClass} ${statusClass}">
                                <input type="checkbox" class="link-checkbox" ${link.wrong_game ? 'checked' : ''} 
                                    onchange="toggleWrongGame(${link.id}, this.checked)" 
                                    title="Mark as wrong game" />
                                <div class="link-details">
                                    <div class="link-url">${shortUrl}</div>
                                    <div class="link-meta">
                                        <span class="link-status-badge ${link.status}">${link.status}</span>
                                        ${link.channel_name ? `<span>${link.channel_name}</span>` : ''}
                                        <span>${link.date_tested}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    linksList.innerHTML = html;
                } else {
                    linksList.innerHTML = '<div class="links-empty">No links found for this game</div>';
                }
            } catch (error) {
                linksList.innerHTML = '<div class="links-empty">Error loading links</div>';
                console.error('Error loading links:', error);
            }
        }
        
        async function toggleWrongGame(linkId, wrongGame) {
            try {
                const response = await fetch('/api/toggle-wrong-game', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        link_id: linkId,
                        wrong_game: wrongGame
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Reload links list to reflect changes
                    loadLinksList();
                } else {
                    alert('Error: ' + (data.error || 'Failed to update link'));
                }
            } catch (error) {
                alert('Error updating link: ' + error.message);
            }
        }
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


# ==================== Database Functions ====================

def init_database():
    """Initialize the SQLite database for tracking good/bad links"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            game_url TEXT NOT NULL,
            source TEXT,
            first_seen_date TEXT NOT NULL,
            last_seen_date TEXT NOT NULL,
            UNIQUE(game_url)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_url TEXT NOT NULL,
            stream_url TEXT NOT NULL,
            channel_name TEXT,
            source_url TEXT,
            date_tested TEXT NOT NULL,
            status TEXT NOT NULL,
            test_duration REAL,
            error_message TEXT,
            wrong_game INTEGER DEFAULT 0,
            FOREIGN KEY (game_url) REFERENCES games (game_url),
            UNIQUE(game_url, stream_url, date_tested)
        )
    ''')
    
    # Add wrong_game column to existing tables if it doesn't exist
    try:
        c.execute('ALTER TABLE links ADD COLUMN wrong_game INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_game_url ON links(game_url)
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_date_status ON links(date_tested, status)
    ''')
    
    conn.commit()
    conn.close()
    print(f"[Database] ✓ Initialized database: {DB_FILE}")


def is_new_day():
    """Check if this is a new day since last run"""
    global last_run_date
    today = date.today()
    
    # Try to read last run date from file
    last_run_file = '.last_run_date'
    if os.path.exists(last_run_file):
        try:
            with open(last_run_file, 'r') as f:
                stored_date = f.read().strip()
                last_run_date = datetime.strptime(stored_date, '%Y-%m-%d').date()
        except:
            last_run_date = None
    
    if last_run_date is None or last_run_date < today:
        # Save current date
        with open(last_run_file, 'w') as f:
            f.write(today.strftime('%Y-%m-%d'))
        last_run_date = today
        return True
    
    return False


def should_track_game(game_title, game_url):
    """Check if a game should be tracked in the database"""
    game_lower = (game_title + " " + game_url).lower()
    return any(tracked in game_lower for tracked in TRACKED_GAMES)


def test_stream_link(stream_url, timeout=5):
    """Test if a stream URL is working (good) or not (bad)"""
    try:
        # Quick HEAD request to check if URL is accessible
        headers = HEADERS.copy()
        response = requests.head(stream_url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
        
        # If HEAD is not supported, try GET with range
        if response.status_code == 405:
            headers['Range'] = 'bytes=0-1024'
            response = requests.get(stream_url, headers=headers, timeout=timeout, verify=False, stream=True)
        
        if response.status_code == 200 or response.status_code == 206:
            # Check if it's actually an m3u8 or valid stream
            content_type = response.headers.get('Content-Type', '')
            if 'm3u8' in stream_url.lower() or 'video' in content_type.lower() or 'application' in content_type.lower():
                return True, None
            # Also check response content if it's a text file
            if 'text' in content_type.lower():
                try:
                    content = response.text[:1000]  # Check first 1000 chars
                    if '.m3u8' in content or 'EXTM3U' in content or 'EXTINF' in content:
                        return True, None
                except:
                    pass
        
        return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, str(e)[:100]  # Limit error message length


def record_game(game_title, game_url, source):
    """Record a game in the database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    today_str = date.today().strftime('%Y-%m-%d')
    
    try:
        c.execute('''
            INSERT OR REPLACE INTO games (game_name, game_url, source, first_seen_date, last_seen_date)
            VALUES (?, ?, ?, 
                COALESCE((SELECT first_seen_date FROM games WHERE game_url = ?), ?),
                ?)
        ''', (game_title, game_url, source, game_url, today_str, today_str))
        
        conn.commit()
    except Exception as e:
        print(f"[Database] ✗ Error recording game: {e}")
    finally:
        conn.close()


def record_link_status(game_url, stream_url, channel_name, source_url, is_good, error_msg=None, test_duration=None):
    """Record whether a link is good or bad for today"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    today_str = date.today().strftime('%Y-%m-%d')
    status = 'good' if is_good else 'bad'
    
    try:
        c.execute('''
            INSERT OR REPLACE INTO links 
            (game_url, stream_url, channel_name, source_url, date_tested, status, test_duration, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (game_url, stream_url, channel_name, source_url, today_str, status, test_duration, error_msg))
        
        conn.commit()
        print(f"[Database] ✓ Recorded {status} link: {stream_url[:60]}...")
    except Exception as e:
        print(f"[Database] ✗ Error recording link status: {e}")
    finally:
        conn.close()


def get_good_links_for_game(game_url, today_only=True):
    """Get all known good links for a game (excluding wrong_game links)"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    today_str = date.today().strftime('%Y-%m-%d')
    
    try:
        if today_only:
            c.execute('''
                SELECT stream_url, channel_name, source_url
                FROM links
                WHERE game_url = ? AND date_tested = ? AND status = 'good' AND (wrong_game = 0 OR wrong_game IS NULL)
                ORDER BY id DESC
            ''', (game_url, today_str))
        else:
            # Get links from last 7 days
            c.execute('''
                SELECT stream_url, channel_name, source_url
                FROM links
                WHERE game_url = ? AND date_tested >= date('now', '-7 days') AND status = 'good' AND (wrong_game = 0 OR wrong_game IS NULL)
                ORDER BY date_tested DESC, id DESC
            ''', (game_url,))
        
        results = c.fetchall()
        return [{'stream_url': r[0], 'channel_name': r[1], 'source_url': r[2]} for r in results]
    except Exception as e:
        print(f"[Database] ✗ Error getting good links: {e}")
        return []
    finally:
        conn.close()


def get_bad_links_for_game(game_url, today_only=True):
    """Get all known bad links for a game to avoid retesting"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    today_str = date.today().strftime('%Y-%m-%d')
    
    try:
        if today_only:
            c.execute('''
                SELECT stream_url
                FROM links
                WHERE game_url = ? AND date_tested = ? AND status = 'bad'
            ''', (game_url, today_str))
        else:
            # Get bad links from last 3 days
            c.execute('''
                SELECT stream_url
                FROM links
                WHERE game_url = ? AND date_tested >= date('now', '-3 days') AND status = 'bad'
            ''', (game_url,))
        
        results = c.fetchall()
        return {r[0] for r in results}  # Return as set for fast lookup
    except Exception as e:
        print(f"[Database] ✗ Error getting bad links: {e}")
        return set()
    finally:
        conn.close()


def get_links_for_game(game_url, include_wrong_game=False):
    """Get all links for a game with full details"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        query = '''
            SELECT id, stream_url, channel_name, status, date_tested, wrong_game, error_message
            FROM links
            WHERE game_url = ?
        '''
        if not include_wrong_game:
            query += ' AND (wrong_game = 0 OR wrong_game IS NULL)'
        query += ' ORDER BY date_tested DESC, id DESC'
        
        c.execute(query, (game_url,))
        results = c.fetchall()
        return [{
            'id': r[0],
            'stream_url': r[1],
            'channel_name': r[2],
            'status': r[3],
            'date_tested': r[4],
            'wrong_game': bool(r[5]) if r[5] is not None else False,
            'error_message': r[6]
        } for r in results]
    except Exception as e:
        print(f"[Database] ✗ Error getting links: {e}")
        return []
    finally:
        conn.close()


def toggle_wrong_game_flag(link_id, wrong_game):
    """Toggle the wrong_game flag for a link"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE links
            SET wrong_game = ?
            WHERE id = ?
        ''', (1 if wrong_game else 0, link_id))
        conn.commit()
        print(f"[Database] ✓ Updated link {link_id}: wrong_game = {wrong_game}")
        return True
    except Exception as e:
        print(f"[Database] ✗ Error updating wrong_game flag: {e}")
        return False
    finally:
        conn.close()


def get_database_stats():
    """Get statistics about the database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        today_str = date.today().strftime('%Y-%m-%d')
        
        # Count games tracked
        c.execute('SELECT COUNT(*) FROM games')
        total_games = c.fetchone()[0]
        
        # Count links tested today
        c.execute('SELECT COUNT(*) FROM links WHERE date_tested = ?', (today_str,))
        links_today = c.fetchone()[0]
        
        # Count good vs bad today
        c.execute('SELECT COUNT(*) FROM links WHERE date_tested = ? AND status = ?', (today_str, 'good'))
        good_today = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM links WHERE date_tested = ? AND status = ?', (today_str, 'bad'))
        bad_today = c.fetchone()[0]
        
        return {
            'total_games': total_games,
            'links_today': links_today,
            'good_today': good_today,
            'bad_today': bad_today
        }
    except Exception as e:
        print(f"[Database] ✗ Error getting stats: {e}")
        return {}
    finally:
        conn.close()


# ==================== End Database Functions ====================


def fetch_fresh_stream_url():
    """Fetch a fresh stream URL with new security token"""
    global current_stream_url, last_refresh_time, stream_info
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching fresh stream URL...")
    
    try:
        # Step 1: Get main page
        print("→ Fetching main page...")
        response = requests.get(MAIN_PAGE_URL, headers=HEADERS, timeout=10, verify=False)
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
        iframe_response = requests.get(iframe_url, headers=headers_with_referrer, timeout=10, verify=False)
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


def search_rojadirecta_games(keywords):
    """Search for games on Rojadirecta"""
    try:
        print(f"[Rojadirecta] Searching for: {keywords}")
        response = requests.get('https://rojadirectame.eu/football', headers=HEADERS, timeout=10, verify=False)
        
        if response.status_code != 200:
            print(f"[Rojadirecta] Failed to fetch page: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find all game links - Rojadirecta uses <a> tags with /football/ in href
        all_links = soup.find_all('a', href=True)
        print(f"[Rojadirecta] Found {len(all_links)} total links")
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Look for links to specific games (contains team names and event-like patterns)
            if '/football/' in href and href.count('/') >= 2:
                full_url = urljoin('https://rojadirectame.eu', href)
                
                # Extract game title - prefer URL slug over generic link text
                url_slug = href.split('/')[-1].split('?')[0]  # Get last part, remove query params
                
                # If link text is generic (like "watch", "live", etc) or too short, use URL slug
                if len(text) < 8 or text.lower() in ['watch', 'live', 'stream', 'ver', 'watch now', 'live stream']:
                    game_title = url_slug.replace('-', ' ').title()
                else:
                    game_title = text
                
                # Check if keywords match (check both title and URL)
                keywords_lower = keywords.lower()
                title_lower = game_title.lower()
                href_lower = href.lower()
                
                if any(kw.lower() in title_lower or kw.lower() in href_lower for kw in keywords.split()):
                    # Calculate match score
                    match_score = sum(1 for kw in keywords_lower.split() if kw in title_lower or kw in href_lower)
                    
                    results.append({
                        'title': game_title,
                        'url': full_url,
                        'source': 'Rojadirecta',
                        'time': '',
                        'match_score': match_score
                    })
                    print(f"[Rojadirecta] ✓ Found: {game_title[:50]}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        print(f"[Rojadirecta] Found {len(unique_results)} matching game(s)")
        return unique_results
        
    except Exception as e:
        print(f"[Rojadirecta] Search error: {e}")
        return []


def extract_all_streams_from_rojadirecta(event_url):
    """Extract ALL working stream URLs from a Rojadirecta event page"""
    working_streams = []
    try:
        print(f"[Rojadirecta] Fetching event page: {event_url}")
        response = requests.get(event_url, headers=HEADERS, timeout=10, verify=False)
        
        if response.status_code != 200:
            print(f"[Rojadirecta] Failed to fetch event page: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        stream_channels = []
        
        # Rojadirecta uses nested iframes - we need to follow them
        # Step 1: Get all iframes from main page
        iframes = soup.find_all('iframe', src=True)
        print(f"[Rojadirecta] Found {len(iframes)} iframe(s) on main page")
        
        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                full_url = urljoin(event_url, src) if not src.startswith('http') else src
                if full_url.startswith('//'):
                    full_url = 'https:' + full_url
                    
                stream_channels.append({
                    'url': full_url,
                    'name': f"Rojadirecta Stream {len(stream_channels) + 1}",
                    'priority': 0,
                    'referer': event_url
                })
        
        # Look for all links that might be stream channels
        all_links = soup.find_all('a', href=True)
        print(f"[Rojadirecta] Found {len(all_links)} total links")
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Skip junk
            if any(skip in href.lower() for skip in ['facebook', 'twitter', 'instagram', 'google.com', 'adobe.com']):
                continue
            
            # Look for stream-like links
            if any(x in href.lower() for x in ['stream', 'player', 'watch', 'live', 'embed', '.php']):
                full_url = urljoin(event_url, href) if not href.startswith('http') else href
                if full_url.startswith('//'):
                    full_url = 'https:' + full_url
                    
                channel_name = text if text else f"Rojadirecta Channel {len(stream_channels) + 1}"
                
                stream_channels.append({
                    'url': full_url,
                    'name': channel_name,
                    'priority': 1
                })
        
        # Sort by priority
        stream_channels.sort(key=lambda x: x['priority'])
        
        # Deduplicate
        seen_urls = set()
        unique_channels = []
        for channel in stream_channels:
            if channel['url'] not in seen_urls:
                seen_urls.add(channel['url'])
                unique_channels.append(channel)
        
        print(f"[Rojadirecta] Found {len(unique_channels)} unique channel(s) to try")
        
        # Try each channel
        for i, channel in enumerate(unique_channels, 1):
            try:
                print(f"[Rojadirecta] [{i}/{len(unique_channels)}] Trying {channel['name']}: {channel['url'][:60]}...")
                headers_with_ref = HEADERS.copy()
                headers_with_ref['Referer'] = event_url
                
                channel_response = requests.get(channel['url'], headers=headers_with_ref, timeout=10, verify=False)
                print(f"[Rojadirecta]   Response: {channel_response.status_code}, Size: {len(channel_response.text)} bytes")
                
                # Look for .m3u8 URLs with multiple patterns
                patterns = [
                    r'source["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'src["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'https?://[^\s"\'\)]+\.m3u8[^\s"\'\)]*',
                    r'["\'](https?://[^"\']*(?:stream|live|hls)[^"\']*\.m3u8[^"\']*)["\']'
                ]
                
                found_stream = False
                for pattern in patterns:
                    m3u8_matches = re.findall(pattern, channel_response.text)
                    if m3u8_matches:
                        for match in m3u8_matches[:3]:  # Try first 3 matches
                            stream_url = match.replace('&amp;', '&')
                            
                            # Accept if URL looks valid
                            if stream_url.startswith('http') and '.m3u8' in stream_url:
                                print(f"[Rojadirecta] ✓ Found stream from {channel['name']}: {stream_url[:60]}...")
                                working_streams.append({
                                    'url': stream_url,
                                    'name': channel['name'],
                                    'source_url': channel['url']
                                })
                                found_stream = True
                                break
                        if found_stream:
                            break
                
                # Look for nested iframes and follow them
                if not found_stream:
                    nested_soup = BeautifulSoup(channel_response.text, 'html.parser')
                    
                    # Check for JavaScript-embedded iframe URLs
                    # Rojadirecta uses: document.write('<iframe ... src="URL"></iframe>')
                    js_iframe_pattern = r'src=["\'](https?://[^"\']+\.php[^"\']*)["\']'
                    js_matches_raw = re.findall(js_iframe_pattern, channel_response.text)
                    # Clean URLs - remove query parameters except hash (complex URLs return empty responses)
                    js_matches = []
                    for url in js_matches_raw:
                        # If it has query params with hash, simplify to just hash param
                        if '?hash=' in url and '&' in url:
                            base_url = url.split('?')[0]
                            hash_match = re.search(r'[?&]hash=([^&]+)', url)
                            if hash_match:
                                clean_url = f"{base_url}?hash={hash_match.group(1)}"
                                js_matches.append(clean_url)
                                print(f"[Rojadirecta]   Cleaned URL: {url[:60]}... -> {clean_url[:60]}...")
                        else:
                            js_matches.append(url)  # Keep as-is if no extra params
                    
                    # Also check for regular <script src="..."> tags
                    script_tags = nested_soup.find_all('script', src=True)
                    script_urls = [urljoin(channel['url'], s.get('src')) for s in script_tags if s.get('src')]
                    
                    # Try to fetch JavaScript files that might contain iframe URLs
                    for script_url in script_urls:
                        try:
                            print(f"[Rojadirecta]   Checking script: {script_url[:60]}...")
                            script_response = requests.get(script_url, headers=headers_with_ref, timeout=5, verify=False)
                            js_iframe_urls_raw = re.findall(js_iframe_pattern, script_response.text)
                            if js_iframe_urls_raw:
                                print(f"[Rojadirecta]     Found {len(js_iframe_urls_raw)} iframe URLs in script")
                                # Clean these URLs too
                                for url in js_iframe_urls_raw:
                                    if '?hash=' in url and '&' in url:
                                        base_url = url.split('?')[0]
                                        hash_match = re.search(r'[?&]hash=([^&]+)', url)
                                        if hash_match:
                                            clean_url = f"{base_url}?hash={hash_match.group(1)}"
                                            js_matches.append(clean_url)
                                            print(f"[Rojadirecta]     Cleaned URL to: {clean_url[:60]}...")
                                    else:
                                        js_matches.append(url)
                        except Exception as e:
                            print(f"[Rojadirecta]     Script error: {str(e)[:30]}")
                            pass
                    
                    # Follow nested iframes
                    nested_iframes = nested_soup.find_all('iframe')
                    all_nested_urls = []
                    
                    # Add iframes from HTML
                    for nested_iframe in nested_iframes:
                        nested_src = nested_iframe.get('src', '')
                        if nested_src:
                            if nested_src.startswith('//'):
                                nested_src = 'https:' + nested_src
                            elif nested_src.startswith('/'):
                                nested_src = urljoin(channel['url'], nested_src)
                            elif not nested_src.startswith('http'):
                                nested_src = urljoin(channel['url'], nested_src)
                            all_nested_urls.append(nested_src)
                    
                    # Add iframes from JavaScript
                    for js_url in js_matches:
                        if js_url not in all_nested_urls:
                            all_nested_urls.append(js_url)
                    
                    # Follow each nested iframe URL
                    # Use the immediate parent (channel URL) as Referer for better results
                    nested_headers = HEADERS.copy()
                    nested_headers['Referer'] = channel['url']
                    
                    for nested_url in all_nested_urls[:5]:  # Limit to 5 levels deep
                        try:
                            print(f"[Rojadirecta]   Following nested iframe: {nested_url[:60]}...")
                            nested_response = requests.get(nested_url, headers=nested_headers, timeout=10, verify=False)
                            print(f"[Rojadirecta]     Response: {nested_response.status_code}, {len(nested_response.text)} bytes")
                            
                            # Look for .m3u8 in the nested page
                            for pattern in patterns:
                                m3u8_matches = re.findall(pattern, nested_response.text)
                                if m3u8_matches:
                                    print(f"[Rojadirecta]     Pattern matched {len(m3u8_matches)} potential stream(s)")
                                    for match in m3u8_matches[:2]:
                                        stream_url = match.replace('&amp;', '&')
                                        if stream_url.startswith('http') and '.m3u8' in stream_url:
                                            print(f"[Rojadirecta] ✓ Found stream in nested iframe: {stream_url[:60]}...")
                                            working_streams.append({
                                                'url': stream_url,
                                                'name': channel['name'],
                                                'source_url': channel['url']
                                            })
                                            found_stream = True
                                            break
                                if found_stream:
                                    break
                            if found_stream:
                                break
                        except Exception as e:
                            print(f"[Rojadirecta]   ✗ Nested iframe failed: {str(e)[:40]}")
                            continue
                            
            except Exception as e:
                print(f"[Rojadirecta]   ✗ Failed: {str(e)[:50]}")
                continue
        
        print(f"[Rojadirecta] ✓ Found {len(working_streams)} working stream(s)")
        return working_streams
        
    except Exception as e:
        print(f"[Rojadirecta] ✗ Error extracting streams: {e}")
        return []


def search_livetv_games(keywords):
    """Search for games on LiveTV.sx and LiveTV 872 matching the keywords"""
    games = []
    
    # List of LiveTV domains to check (primary first, then alternatives)
    livetv_domains = [
        ('https://livetv.sx', 'LiveTV.sx'),
        ('https://livetv872.me', 'LiveTV 872')
    ]
    
    for base_url, source_name in livetv_domains:
        try:
            # Use NFL-specific page (sport ID 27) for NFL-related searches
            # Check if keywords are NFL-related
            nfl_keywords = ['nfl', 'patriots', 'browns', 'bills', 'dolphins', 'jets', 'ravens', 
                           'bengals', 'steelers', 'texans', 'colts', 'jaguars', 'titans',
                           'chiefs', 'raiders', 'chargers', 'broncos', 'cowboys', 'giants',
                           'eagles', 'commanders', 'bears', 'lions', 'packers', 'vikings',
                           'falcons', 'panthers', 'saints', 'buccaneers', 'cardinals', 'rams',
                           '49ers', 'seahawks', 'football', 'american football']
            
            keywords_lower = keywords.lower()
            is_nfl_search = any(nfl_kw in keywords_lower for nfl_kw in nfl_keywords)
            
            if is_nfl_search:
                # Use NFL-specific page
                url = f"{base_url}/enx/allupcomingsports/27/"
            else:
                # Use general search or top page
                url = f"{base_url}/enx/"
            
            print(f"\n[Search] Fetching {source_name} from: {url}")
            
            response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links (not just eventinfo links) to catch all patriots references
            all_links = soup.find_all('a', href=True)
            keywords_lower = [k.lower().strip() for k in keywords.split()]
        
            # Expand keywords to include NFL-related terms when searching for specific teams
            # Also, if user searches for a specific team, include all NFL games (broader search)
            search_all_nfl = any(kw in keywords_lower for kw in ['patriots', 'falcons'])
            if search_all_nfl or 'nfl' in keywords_lower:
                keywords_lower.extend(['nfl', 'american football', 'redzone', 'red zone'])
            
            seen_urls = set()
            
            for link in all_links:
                # Get the link text and URL
                link_text = link.get_text(strip=True)
                link_url = link.get('href', '')
                
                # Skip empty links
                if not link_url:
                    continue
                
                # Make URL absolute
                if link_url.startswith('/'):
                    link_url = urljoin(base_url, link_url)
                elif not link_url.startswith('http'):
                    link_url = urljoin(url, link_url)
                
                # Skip if already seen (deduplicate)
                if link_url in seen_urls:
                    continue
                seen_urls.add(link_url)
                
                # Only check eventinfo links
                if '/eventinfo/' not in link_url:
                    continue
                
                # Filter out broken URLs with empty titles (e.g., eventinfo/312314225__/)
                if re.search(r'/eventinfo/\d+__?/', link_url):
                    print(f"[Search] Skipping broken URL: {link_url}")
                    continue
                
                # Check if any keyword matches in text OR URL
                link_text_lower = link_text.lower()
                link_url_lower = link_url.lower()
                match_score = sum(1 for kw in keywords_lower if kw in link_text_lower or kw in link_url_lower)
                
                # IMPORTANT: If URL contains the search keyword, it's a match even if text is empty
                # This catches cases where link text is empty but URL has the team name
                if match_score == 0:
                    # Check URL for keywords (even if link text is empty)
                    if any(kw in link_url_lower for kw in keywords_lower):
                        match_score = 1
                        print(f"[Search] Matched by URL (text was empty/short): {link_url}")
                
                # Also: If searching for "patriots", also match URLs with "new_england" or "atlanta" 
                # (common patterns for Patriots games)
                if match_score == 0 and 'patriots' in keywords_lower:
                    # Check for known Patriots game event IDs or URL patterns
                    known_patriots_event_ids = ['312314225']  # Known Patriots vs Falcons event
                    is_known_patriots_game = any(eid in link_url for eid in known_patriots_event_ids)
                    
                    if is_known_patriots_game or any(alt_term in link_url_lower for alt_term in ['new_england', 'new-england', 'atlanta']):
                        # Only match if it looks like an NFL game (has event ID and reasonable URL structure)
                        if '/eventinfo/' in link_url and re.search(r'/eventinfo/\d+', link_url):
                            match_score = 1
                            if is_known_patriots_game:
                                print(f"[Search] Matched known Patriots game by event ID: {link_url}")
                            else:
                                print(f"[Search] Matched Patriots game by URL pattern (new_england/atlanta): {link_url}")
                
                # If searching for specific teams (patriots/falcons), include ALL NFL games
                if search_all_nfl and match_score == 0:
                    # Check if it's an NFL/American Football game
                    if any(nfl_term in link_text_lower or nfl_term in link_url_lower 
                           for nfl_term in ['nfl', 'american football', 'redzone', 'red zone', 'nfl redzone']):
                        match_score = 1
                        print(f"[Search] Including NFL game (broad search): {link_text}")
                
                # If no keywords provided or "all" keyword, return ALL valid links (up to limit)
                if not keywords_lower or (len(keywords_lower) == 1 and keywords_lower[0] == 'all'):
                    match_score = 1  # Include all valid links
                
                # Filter out false positives (e.g., "Eppan – Fassa Falcons" is not NFL)
                if match_score > 0:
                    # Exclude non-NFL games that match by team name only
                    if any(kw in link_text_lower for kw in ['patriots', 'falcons']) and match_score == 1:
                        # Check if it's clearly not NFL (European teams, etc.)
                        if any(exclude in link_text_lower for exclude in ['eppan', 'fassa', 'ice hockey', 'hockey', 'volleyball', 'basketball']):
                            print(f"[Search] Filtering false positive: {link_text}")
                            continue
                    
                    if '/eventinfo/' in link_url or 'eventinfo' in link_url_lower:
                        # Try to find time/status info
                        time_elem = link.find_parent().find_previous_sibling() if link.find_parent() else None
                        time_text = time_elem.get_text(strip=True) if time_elem else ""
                        
                        # Detect if game is LIVE by checking for score patterns (e.g., "120:117", "0:0", "22:14")
                        # Scores appear near the link in the HTML
                        is_live = False
                        score = None
                        
                        # Check the parent container and siblings for score patterns
                        parent = link.find_parent()
                        if parent:
                            # Get all text in the parent container
                            parent_text = parent.get_text()
                            # Look for score patterns like "120:117", "0:0", "22:14", etc.
                            # Pattern: digits:digits (score format)
                            score_pattern = re.search(r'(\d+):(\d+)', parent_text)
                            if score_pattern:
                                # Check if it's a reasonable score (not a time like "22:30")
                                score_val = score_pattern.group(0)
                                parts = score_val.split(':')
                                if len(parts) == 2:
                                    try:
                                        # If both parts are reasonable scores (0-200 for most sports)
                                        # and not a time (hours are 0-23, minutes 0-59)
                                        score1, score2 = int(parts[0]), int(parts[1])
                                        # If either score is > 59, it's definitely a game score, not time
                                        # Also check if it's in "Top Events LIVE" section
                                        if score1 > 59 or score2 > 59 or 'live' in parent_text.lower()[:100]:
                                            is_live = True
                                            score = score_val
                                        # For NFL, scores are typically lower, but if we see "0:0" or similar in LIVE section, it's live
                                        elif (score1 <= 59 and score2 <= 59) and ('live' in parent_text.lower()[:100] or 'top events live' in parent_text.lower()[:200]):
                                            is_live = True
                                            score = score_val
                                    except ValueError:
                                        pass
                        
                        # Also check if link is in "Top Events LIVE" section
                        # Look for "LIVE" indicators in nearby text
                        if not is_live:
                            # Check siblings and parent for "LIVE" text
                            check_elem = link
                            for _ in range(3):  # Check up to 3 levels up
                                if check_elem:
                                    check_text = check_elem.get_text().lower()
                                    if 'live' in check_text[:50] or 'top events live' in check_text[:100]:
                                        is_live = True
                                        break
                                    check_elem = check_elem.find_parent()
                        
                        # Use link text or extract from URL
                        if not link_text or len(link_text.strip()) < 5:
                            # Try to extract title from URL
                            url_parts = link_url.split('/')
                            for part in url_parts:
                                if any(term in part.lower() for term in ['patriots', 'falcons', 'atlanta', 'new_england', 'new-england']):
                                    # Clean up the title from URL
                                    link_text = part.replace('_', ' ').replace('-', ' ')
                                    # Capitalize properly
                                    words = link_text.split()
                                    link_text = ' '.join(w.capitalize() for w in words)
                                    # Fix common abbreviations
                                    link_text = link_text.replace('New England', 'New England')
                                    break
                            
                            # If still empty, check if URL contains event ID that might be Patriots game
                            if not link_text or len(link_text.strip()) < 5:
                                if '312314225' in link_url:
                                    link_text = 'New England Patriots – Atlanta Falcons'  # Known Patriots game
                        
                        # If still no title, use a default but don't skip it - URL match is enough
                        if not link_text or len(link_text.strip()) < 3:
                            link_text = 'LiveTV Game'  # Default title for URLs that match
                        
                        # Extract event ID for deduplication
                        event_id_match = re.search(r'/eventinfo/(\d+)', link_url)
                        event_id = event_id_match.group(1) if event_id_match else None
                        
                        games.append({
                            'title': link_text if link_text else 'Patriots Game',
                            'url': link_url,
                            'source': source_name,
                            'match_score': match_score,
                            'time': time_text,
                            'event_id': event_id,
                            'is_live': is_live,
                            'score': score
                        })
            
            # Deduplicate by event ID (same game can have multiple URLs) - do this per domain
            domain_games = [g for g in games if g.get('source') == source_name]
            unique_games = []
            seen_event_ids = set()
            seen_game_urls = set()
            
            # First pass: group games by event ID
            games_by_event = {}
            for game in domain_games:
                event_id = game.get('event_id')
                if event_id:
                    if event_id not in games_by_event:
                        games_by_event[event_id] = []
                    games_by_event[event_id].append(game)
            
            # For each event, pick the best URL (one with full title, not empty/broken)
            # But if there are multiple different URLs for same event, include them all
            for event_id, event_games in games_by_event.items():
                # If only one URL, just add it
                if len(event_games) == 1:
                    if event_games[0]['url'] not in seen_game_urls:
                        seen_game_urls.add(event_games[0]['url'])
                        unique_games.append(event_games[0])
                else:
                    # Multiple URLs for same event - prefer ones with good titles, but include all unique URLs
                    # Sort by title quality (non-empty, descriptive)
                    event_games.sort(key=lambda g: (
                        len(g['title']) < 5,  # Prefer longer titles
                        '__' in g['url'],  # Prefer URLs without __
                    ))
                    
                    # Include all unique URLs (up to 3 per event to avoid duplicates)
                    for game in event_games[:3]:
                        if game['url'] not in seen_game_urls:
                            seen_game_urls.add(game['url'])
                            unique_games.append(game)
            
            # Also include games without event IDs (fallback)
            for game in games:
                if not game.get('event_id') and game['url'] not in seen_game_urls:
                    seen_game_urls.add(game['url'])
                    unique_games.append(game)
            
            # PRIORITY EVENT: Always prioritize Tampa Bay Buccaneers vs New England Patriots (has 10 player links)
            priority_event_id = '314788282'
            
            # Helper function to check if a game URL is the priority event
            def is_priority_event_livetv(game_url):
                url_lower = game_url.lower()
                # Match event ID in URL - check for /eventinfo/314788282 or eventinfo/314788282
                return f'/eventinfo/{priority_event_id}' in url_lower or f'eventinfo/{priority_event_id}' in url_lower
            
            # First, always prioritize the specific event with 10 links
            if len(unique_games) > 1:
                # Separate priority event from others
                priority_games = [g for g in unique_games if is_priority_event_livetv(g['url'])]
                other_games = [g for g in unique_games if not is_priority_event_livetv(g['url'])]
                
                if priority_games:
                    print(f"[Search] Found priority event (10 links): {priority_games[0]['url']}")
                    # Put priority games first
                    unique_games = priority_games + other_games
            
            # Sort results to prioritize exact team matches (but keep all valid results)
            if search_all_nfl and len(unique_games) > 1:
                # Find the keyword being searched
                search_keywords = keywords_lower
                has_patriots_search = 'patriots' in search_keywords
                has_falcons_search = 'falcons' in search_keywords
                
                # Sort by: live games > priority event > exact team match > match score > NFL content (but keep all results)
                # Note: Priority event is already first from previous step, this just sorts the rest
                unique_games.sort(key=lambda g: (
                    # HIGHEST PRIORITY: Live games (currently playing)
                    -g.get('is_live', False),
                    # HIGH PRIORITY: The specific event with 10 player links (already first, but keep it here too)
                    -is_priority_event_livetv(g['url']),
                    # Prioritize games that contain the exact search terms in URL or title
                    -(has_patriots_search and ('patriots' in g['title'].lower() or 'patriots' in g['url'].lower())),
                    -(has_falcons_search and ('falcons' in g['title'].lower() or 'falcons' in g['url'].lower())),
                    -(has_patriots_search and ('new_england' in g['url'].lower() or 'new-england' in g['url'].lower())),
                    -(has_falcons_search and 'atlanta' in g['url'].lower()),
                    -g.get('match_score', 0),  # Higher match score first
                    # Demote NFL Redzone (doesn't have team names) - put it last
                    'redzone' in g['title'].lower()
                ))
                print(f"[Search] Sorted {len(unique_games)} results (best matches first)")
            
            # If returning all games, limit to first 20 for performance per domain
            if len(unique_games) > 20:
                unique_games = unique_games[:20]
                print(f"[Search] Limited to first 20 results from {source_name}")
            
            print(f"[Search] Found {len(unique_games)} unique game(s) on {source_name}")
            
            # Add unique games from this domain to the main games list
            games.extend(unique_games)
            
        except Exception as e:
            print(f"[Search] ✗ Error searching {source_name}: {e}")
            import traceback
            traceback.print_exc()
            continue  # Try next domain
    
    # Final deduplication across all domains (by event ID)
    final_unique_games = []
    seen_event_ids_final = set()
    seen_urls_final = set()
    
    # Group by event ID across all domains
    games_by_event_final = {}
    for game in games:
        event_id = game.get('event_id')
        if event_id:
            if event_id not in games_by_event_final:
                games_by_event_final[event_id] = []
            games_by_event_final[event_id].append(game)
        else:
            # Games without event ID - add directly if URL not seen
            if game['url'] not in seen_urls_final:
                seen_urls_final.add(game['url'])
                final_unique_games.append(game)
    
    # For each event, prefer livetv872.me URLs (newer domain) but include both if different
    for event_id, event_games in games_by_event_final.items():
        if event_id not in seen_event_ids_final:
            seen_event_ids_final.add(event_id)
            # Prefer livetv872.me URLs, but include both domains if they're different
            livetv872_games = [g for g in event_games if 'livetv872.me' in g['url']]
            livetv_sx_games = [g for g in event_games if 'livetv.sx' in g['url']]
            
            # Add livetv872.me first (newer domain), then livetv.sx as backup
            if livetv872_games:
                for game in livetv872_games:
                    if game['url'] not in seen_urls_final:
                        seen_urls_final.add(game['url'])
                        final_unique_games.append(game)
            elif livetv_sx_games:
                for game in livetv_sx_games:
                    if game['url'] not in seen_urls_final:
                        seen_urls_final.add(game['url'])
                        final_unique_games.append(game)
    
    # Final sort: prioritize live games, then by match score
    final_unique_games.sort(key=lambda x: (
        -x.get('is_live', False),  # Live games first
        -x.get('match_score', 0)   # Then by match score
    ))
    
    # Limit final results
    if len(final_unique_games) > 50:
        final_unique_games = final_unique_games[:50]
    
    print(f"[Search] ✓ Total found {len(final_unique_games)} unique game(s) across all LiveTV domains")
    
    return final_unique_games


def get_live_nfl_games():
    """Scrape the NFL page (sport ID 27) to find currently live games"""
    live_games = []
    
    # Check both LiveTV domains
    livetv_domains = [
        ('https://livetv872.me', 'LiveTV 872'),
        ('https://livetv.sx', 'LiveTV.sx')
    ]
    
    for base_url, source_name in livetv_domains:
        try:
            url = f"{base_url}/enx/allupcomingsports/27/"
            print(f"\n[Live Games] Fetching from {source_name}: {url}")
            
            response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links in the page
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                link_url = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                if not link_url or '/eventinfo/' not in link_url:
                    continue
                
                # Make URL absolute
                if link_url.startswith('/'):
                    link_url = urljoin(base_url, link_url)
                elif not link_url.startswith('http'):
                    link_url = urljoin(url, link_url)
                
                # Check if this is a live game by looking for score patterns
                parent = link.find_parent()
                is_live = False
                score = None
                
                if parent:
                    parent_text = parent.get_text()
                    # Look for score patterns
                    score_pattern = re.search(r'(\d+):(\d+)', parent_text)
                    if score_pattern:
                        score_val = score_pattern.group(0)
                        parts = score_val.split(':')
                        if len(parts) == 2:
                            try:
                                score1, score2 = int(parts[0]), int(parts[1])
                                # If either score > 59, it's a game score (not time)
                                # Or if it's in a "LIVE" section
                                if score1 > 59 or score2 > 59 or 'live' in parent_text.lower()[:100]:
                                    is_live = True
                                    score = score_val
                                elif (score1 <= 59 and score2 <= 59) and 'live' in parent_text.lower()[:100]:
                                    is_live = True
                                    score = score_val
                            except ValueError:
                                pass
                
                # Also check for "LIVE" indicators
                if not is_live:
                    check_elem = link
                    for _ in range(3):
                        if check_elem:
                            check_text = check_elem.get_text().lower()
                            if 'live' in check_text[:50] or 'top events live' in check_text[:100]:
                                is_live = True
                                break
                            check_elem = check_elem.find_parent()
                
                # Only include if it's a live NFL game
                if is_live and ('nfl' in link_text.lower() or 'american football' in link_text.lower() or 
                               'nfl' in link_url.lower() or any(team in link_text.lower() for team in 
                               ['patriots', 'eagles', 'cowboys', 'giants', '49ers', 'rams', 'chiefs', 'bills'])):
                    # Extract event ID
                    event_id_match = re.search(r'/eventinfo/(\d+)', link_url)
                    event_id = event_id_match.group(1) if event_id_match else None
                    
                    # Use link text or extract from URL
                    if not link_text or len(link_text.strip()) < 5:
                        url_parts = link_url.split('/')
                        for part in url_parts:
                            if any(term in part.lower() for term in ['patriots', 'eagles', 'cowboys', 'giants', '49ers', 'rams']):
                                link_text = part.replace('_', ' ').replace('-', ' ')
                                words = link_text.split()
                                link_text = ' '.join(w.capitalize() for w in words)
                                break
                    
                    if not link_text or len(link_text.strip()) < 3:
                        link_text = 'Live NFL Game'
                    
                    live_games.append({
                        'title': link_text,
                        'url': link_url,
                        'source': source_name,
                        'is_live': True,
                        'score': score,
                        'event_id': event_id,
                        'match_score': 10  # High priority for live games
                    })
        
        except Exception as e:
            print(f"[Live Games] ✗ Error fetching from {source_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Deduplicate by event ID
    unique_live_games = []
    seen_event_ids = set()
    for game in live_games:
        event_id = game.get('event_id')
        if event_id and event_id not in seen_event_ids:
            seen_event_ids.add(event_id)
            unique_live_games.append(game)
        elif not event_id:
            unique_live_games.append(game)
    
    print(f"[Live Games] ✓ Found {len(unique_live_games)} live NFL game(s)")
    return unique_live_games


def extract_stream_from_apl385_player(player_url, referer_url):
    """Extract stream from emb.apl385.me or emb.apl386.me player"""
    try:
        headers = HEADERS.copy()
        headers['Referer'] = referer_url
        
        # First, try to get the HTML
        response = requests.get(player_url, headers=headers, timeout=10, verify=False)
        if response.status_code != 200:
            return None
        
        content = response.text
        
        # Look for .m3u8 URLs in the HTML
        m3u8_pattern = r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
        m3u8_matches = re.findall(m3u8_pattern, content)
        
        # Make URLs absolute
        absolute_matches = []
        for match in m3u8_matches:
            if match.startswith('//'):
                match = 'https:' + match
            absolute_matches.append(match)
        
        if absolute_matches:
            return absolute_matches[0]
        
        # Look for JavaScript variables that might contain stream URLs
        js_patterns = [
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'src\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'url\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'stream\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, content, re.I)
            for match in matches:
                if '.m3u8' in match:
                    if match.startswith('//'):
                        match = 'https:' + match
                    elif not match.startswith('http'):
                        continue
                    return match
        
        return None
        
    except Exception as e:
        return None

def extract_all_streams_from_livetv(event_url):
    """Extract ALL working stream URLs from a LiveTV.sx event page"""
    working_streams = []
    
    try:
        print(f"\n[Extract] Fetching event page: {event_url}")
        
        # Check for hash fragment with webplayer parameters
        # Format: #webplayer_{provider}|{channel_id}|{event_id}|{lid}|{ci}|{si}|{lang}
        hash_fragment = None
        if '#' in event_url:
            hash_part = event_url.split('#', 1)[1]
            if hash_part.startswith('webplayer_'):
                hash_fragment = hash_part
                print(f"[Extract] Found webplayer hash fragment: {hash_fragment}")
        
        # Parse hash fragment if present
        webplayer_params = None
        if hash_fragment:
            try:
                # Remove 'webplayer_' prefix and split by |
                parts = hash_fragment.replace('webplayer_', '').split('|')
                if len(parts) >= 7:
                    provider = parts[0]
                    channel_id = parts[1]
                    event_id = parts[2]
                    lid = parts[3]
                    ci = parts[4]
                    si = parts[5]
                    lang = parts[6]
                    
                    webplayer_params = {
                        'provider': provider,
                        'channel_id': channel_id,
                        'event_id': event_id,
                        'lid': lid,
                        'ci': ci,
                        'si': si,
                        'lang': lang
                    }
                    print(f"[Extract] Parsed webplayer params: channel={channel_id}, event={event_id}, lid={lid}, ci={ci}, si={si}, lang={lang}")
            except Exception as e:
                print(f"[Extract] Failed to parse hash fragment: {e}")
        
        # Remove hash fragment from URL for fetching the page (but keep it for reference)
        base_event_url = event_url.split('#')[0]
        
        # If we have webplayer parameters from hash, construct webplayer URL directly
        if webplayer_params:
            # Determine which CDN to use based on source domain
            base_url_clean = base_event_url.lower()
            if 'livetv872.me' in base_url_clean:
                # Prefer CDN that matches the domain
                cdn_domains = [
                    'https://cdn.livetv872.me',
                    'https://cdn.livetv869.me',
                    'https://cdn.livetv868.me'
                ]
            else:
                # Default to standard CDN
                cdn_domains = [
                    'https://cdn.livetv869.me',
                    'https://cdn.livetv872.me',
                    'https://cdn.livetv868.me'
                ]
            
            # Construct webplayer URLs with the primary CDN
            primary_cdn = cdn_domains[0]
            
            # Try webplayer.iframe.php first (most direct)
            iframe_url = f"{primary_cdn}/export/webplayer.iframe.php?t={webplayer_params['provider']}&c={webplayer_params['channel_id']}&eid={webplayer_params['event_id']}&lid={webplayer_params['lid']}&lang={webplayer_params['lang']}&m&dmn="
            webplayer2_url = f"{primary_cdn}/webplayer2.php?t={webplayer_params['provider']}&c={webplayer_params['channel_id']}&lang={webplayer_params['lang']}&eid={webplayer_params['event_id']}&lid={webplayer_params['lid']}&ci={webplayer_params['ci']}&si={webplayer_params['si']}"
            webplayer_url = f"{primary_cdn}/webplayer.php?t=ifr&c={webplayer_params['channel_id']}&lang={webplayer_params['lang']}&eid={webplayer_params['event_id']}&lid={webplayer_params['lid']}&ci={webplayer_params['ci']}&si={webplayer_params['si']}"
            
            # Try to extract actual .m3u8 stream from iframe player
            print(f"[Extract] Trying webplayer.iframe.php to extract stream...")
            try:
                headers = HEADERS.copy()
                headers['Referer'] = base_event_url
                iframe_response = requests.get(iframe_url, headers=headers, timeout=10, verify=False)
                if iframe_response.status_code == 200:
                    iframe_content = iframe_response.text
                    
                    # Look for APL385/APL386 player embeds
                    apl385_patterns = [
                        r'(?:https?:)?//emb\.apl38[56]\.me/[^\s"\'<>]+',
                        r'emb\.apl38[56]\.me/player/[^\s"\'<>]+',
                        r'src=["\']([^"\']*emb\.apl38[56]\.me[^"\']*)["\']',
                        r'iframe[^>]+src=["\']([^"\']*apl38[56][^"\']*)["\']',
                    ]
                    
                    for pattern in apl385_patterns:
                        apl385_matches = re.findall(pattern, iframe_content, re.I)
                        if apl385_matches:
                            apl385_url = apl385_matches[0] if isinstance(apl385_matches[0], str) else apl385_matches[0]
                            # Clean up URL (remove newlines/whitespace)
                            apl385_url = re.sub(r'\s+', '', apl385_url)
                            # Make URL absolute
                            if apl385_url.startswith('//'):
                                apl385_url = 'https:' + apl385_url
                            elif not apl385_url.startswith('http'):
                                apl385_url = 'https://' + apl385_url
                            
                            print(f"[Extract] Found APL385/APL386 player: {apl385_url}")
                            # Extract stream from APL385 player
                            stream_url = extract_stream_from_apl385_player(apl385_url, iframe_url)
                            if stream_url:
                                working_streams.append({
                                    'url': stream_url,
                                    'name': f"Channel {webplayer_params['channel_id']} (direct stream)",
                                    'priority': 15,  # Highest priority - direct stream
                                    'referer': base_event_url
                                })
                                print(f"[Extract] ✓ Extracted direct stream from APL385 player: {stream_url}")
                                return working_streams
                            break
            except Exception as e:
                print(f"[Extract] Error extracting from iframe: {e}")
            
            # Fallback to webplayer URLs if direct extraction failed
            working_streams.append({
                'url': iframe_url,
                'name': f"Channel {webplayer_params['channel_id']} (iframe)",
                'priority': 12,  # High priority
                'referer': base_event_url
            })
            working_streams.append({
                'url': webplayer2_url,
                'name': f"Channel {webplayer_params['channel_id']} (webplayer2)",
                'priority': 11,  # High priority
                'referer': base_event_url
            })
            working_streams.append({
                'url': webplayer_url,
                'name': f"Channel {webplayer_params['channel_id']} (webplayer)",
                'priority': 10,  # High priority
                'referer': base_event_url
            })
            print(f"[Extract] ✓ Constructed webplayer URLs from hash")
            
            # Return the streams (prioritized by direct stream > iframe > webplayer2 > webplayer)
            if working_streams:
                print(f"[Extract] Returning {len(working_streams)} stream(s) from hash fragment")
                return working_streams
        
        # Fetch the page (base_event_url was already defined above)
        response = requests.get(base_event_url, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # First, look for hidden link containers (from "Show all" functionality)
        # These are elements with id containing "hidden" that might be hidden by default
        hidden_containers = soup.find_all(id=re.compile(r'hidden', re.I))
        print(f"[Extract] Found {len(hidden_containers)} hidden link container(s)")
        
        # Method 1: Find all stream channel links (LiveTV.sx structure)
        stream_channels = []
        
        # Look for all links - be more aggressive (includes hidden ones)
        all_links = soup.find_all('a', href=True)
        print(f"[Extract] Found {len(all_links)} total links on page (including hidden)")
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            onclick = link.get('onclick', '')
            
            # Skip junk links
            if any(skip in href.lower() for skip in ['lng.php', 'getbanner', 'facebook', 'twitter', 'instagram', 'google.com/share', 'adobe.com', '/enx/', '/eng/']):
                continue
            
            # LiveTV.sx specific: webplayer.php links (with or without onclick)
            # Also check onclick handlers that might contain webplayer URLs
            onclick = link.get('onclick', '')
            if 'webplayer.php' in href or ('webplayer.php' in onclick and ('openWin' in onclick or 'window.open' in onclick)):
                # Extract URL from href or onclick
                url_to_use = href
                if not url_to_use and onclick:
                    # Try to extract URL from onclick
                    onclick_match = re.search(r'["\']([^"\']*webplayer\.php[^"\']*)["\']', onclick)
                    if onclick_match:
                        url_to_use = onclick_match.group(1)
                
                if not url_to_use or 'webplayer.php' not in url_to_use:
                    continue
                
                # Handle protocol-relative URLs
                full_url = url_to_use
                if full_url.startswith('//'):
                    full_url = 'https:' + full_url
                elif not full_url.startswith('http'):
                    # Construct full URL for cdn.livetv869.me webplayer links
                    if 'cdn.livetv869.me' in full_url or full_url.startswith('/'):
                        if not full_url.startswith('http'):
                            if full_url.startswith('//'):
                                full_url = 'https:' + full_url
                            elif full_url.startswith('/'):
                                full_url = 'https://cdn.livetv869.me' + full_url
                            else:
                                full_url = 'https://cdn.livetv869.me/webplayer.php?' + full_url.split('?')[-1] if '?' in full_url else 'https://cdn.livetv869.me/' + full_url
                    else:
                        full_url = urljoin(event_url, full_url)
                
                # Extract channel number for naming
                channel_match = re.search(r'[&?]c=(\d+)', url_to_use)
                channel_name = f"Channel {channel_match.group(1)}" if channel_match else "Stream Channel"
                
                # Check if it's in a hidden container (for logging)
                parent = link.find_parent(id=re.compile(r'hidden', re.I))
                if parent:
                    print(f"[Extract]   Found hidden link: {channel_name}")
                
                stream_channels.append({
                    'url': full_url,
                    'name': channel_name,
                    'priority': 0  # High priority
                })
                continue
            
            # Check if it's a stream channel link - expanded patterns
            if any(x in href.lower() for x in ['/player/', '/stream/', '/watch/', 'iframe', 'webplayer', '.php', '/live/', '/channel']):
                full_url = urljoin(event_url, href) if not href.startswith('http') else href
                if full_url.startswith('//'):
                    full_url = 'https:' + full_url
                    
                channel_name = link.get_text(strip=True) or "Channel"
                
                stream_channels.append({
                    'url': full_url,
                    'name': channel_name,
                    'priority': 1
                })
            
            # Also check onclick attributes for other stream URLs
            elif onclick and ('openWin' in onclick or 'window.open' in onclick):
                url_match = re.search(r"(?:openWin|window\.open)\(['\"]([^'\"]+)['\"]", onclick)
                if url_match:
                    full_url = url_match.group(1)
                    if full_url.startswith('//'):
                        full_url = 'https:' + full_url
                    elif not full_url.startswith('http'):
                        full_url = urljoin(event_url, full_url)
                        
                    stream_channels.append({
                        'url': full_url,
                        'name': link.get_text(strip=True) or "Channel",
                        'priority': 0
                    })
        
        # Method 2: Look for iframes directly on the page
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(event_url, src)
                
                if 'stream' in src.lower() or 'play' in src.lower():
                    stream_channels.append({
                        'url': src,
                        'name': 'Embedded Player',
                        'priority': 0
                    })
        
        # Method 3: Try API endpoint for channel list
        # Some LiveTV.sx pages load channels via API
        event_id_match = re.search(r'/eventinfo/(\d+)', event_url)
        event_id = event_id_match.group(1) if event_id_match else None
        
        if event_id and len([ch for ch in stream_channels if 'webplayer.php' in ch['url']]) < 8:
            print(f"[Extract] Trying API endpoint for event {event_id}...")
            try:
                api_url = f"https://livetv.sx/api/channels?eid={event_id}"
                api_headers = HEADERS.copy()
                api_response = requests.get(api_url, headers=api_headers, timeout=5, verify=False)
                if api_response.status_code == 200:
                    api_soup = BeautifulSoup(api_response.text, 'html.parser')
                    api_links = api_soup.find_all('a', href=True)
                    
                    for link in api_links:
                        href = link.get('href', '')
                        onclick = link.get('onclick', '')
                        
                        # Check href for webplayer.php
                        if 'webplayer.php' in href:
                            if href.startswith('//'):
                                full_url = 'https:' + href
                            elif not href.startswith('http'):
                                full_url = urljoin('https://cdn.livetv869.me', href)
                            else:
                                full_url = href
                            
                            channel_match = re.search(r'[&?]c=(\d+)', href)
                            channel_name = f"Channel {channel_match.group(1)}" if channel_match else "Stream Channel"
                            
                            if not any(ch['url'] == full_url for ch in stream_channels):
                                stream_channels.append({
                                    'url': full_url,
                                    'name': channel_name,
                                    'priority': 0
                                })
                                print(f"[Extract]   Found webplayer link from API: {channel_name}")
                        
                        # Check onclick for webplayer.php
                        if 'webplayer.php' in onclick:
                            onclick_match = re.search(r'["\']([^"\']*webplayer\.php[^"\']*)["\']', onclick)
                            if onclick_match:
                                url_from_onclick = onclick_match.group(1)
                                if url_from_onclick.startswith('//'):
                                    full_url = 'https:' + url_from_onclick
                                elif not url_from_onclick.startswith('http'):
                                    full_url = urljoin('https://cdn.livetv869.me', url_from_onclick)
                                else:
                                    full_url = url_from_onclick
                                
                                channel_match = re.search(r'[&?]c=(\d+)', url_from_onclick)
                                channel_name = f"Channel {channel_match.group(1)}" if channel_match else "Stream Channel"
                                
                                if not any(ch['url'] == full_url for ch in stream_channels):
                                    stream_channels.append({
                                        'url': full_url,
                                        'name': channel_name,
                                        'priority': 0
                                    })
                                    print(f"[Extract]   Found webplayer link from API onclick: {channel_name}")
            except Exception as e:
                print(f"[Extract] API endpoint check failed: {e}")
        
        # Method 4: Search raw HTML for channel IDs if webplayer links weren't found
        # This handles dynamically generated links
        webplayer_count = len([ch for ch in stream_channels if 'webplayer.php' in ch['url']])
        print(f"[Extract] Found {webplayer_count} webplayer links total")
        
        if webplayer_count < 8 and event_id:
            
            if event_id:
                print(f"[Extract] Searching HTML and JavaScript for channel IDs for event {event_id}...")
                # Search HTML for patterns that might contain channel IDs
                html_text = response.text
                
                # Pattern 1: Find all instances of c=XXXXXXX or c:XXXXXXX in HTML
                # This catches onclick handlers, JavaScript, etc.
                c_param_pattern = r'[&?]c[=:](\d{6,7})'
                c_param_channels = re.findall(c_param_pattern, html_text)
                
                # Pattern 2: Find channel numbers in onclick handlers
                onclick_pattern = r'onclick\s*=\s*["\'][^"\']*c[=:](\d{6,7})'
                onclick_channels = re.findall(onclick_pattern, html_text)
                
                # Pattern 3: Find JavaScript arrays with channel numbers (more flexible)
                # Match arrays like [2661185, 2867208, ...] or ["2661185", "2867208"]
                js_array_patterns = [
                    r'\[(\d{6,7}(?:\s*,\s*\d{6,7})*)\]',  # [2661185, 2867208]
                    r'\[["\'](\d{6,7})["\'](?:\s*,\s*["\'](\d{6,7})["\'])*\]',  # ["2661185", "2867208"]
                    r'channels?\s*[=:]\s*\[([^\]]+)\]',  # channels = [2661185, ...]
                ]
                
                found_channels = set(c_param_channels + onclick_channels)
                
                # Extract from JavaScript arrays
                for pattern in js_array_patterns:
                    arrays = re.findall(pattern, html_text, re.IGNORECASE)
                    for array_match in arrays:
                        # Handle tuple results
                        if isinstance(array_match, tuple):
                            numbers = [n for n in array_match if n and n.isdigit()]
                        else:
                            numbers = re.findall(r'\b(\d{6,7})\b', str(array_match))
                        found_channels.update(numbers)
                
                # Pattern 4: Look for AJAX/fetch endpoints that might load channels
                ajax_patterns = [
                    r'fetch\(["\']([^"\']*eid[^"\']*)["\']',
                    r'\.ajax\(["\']([^"\']*eid[^"\']*)["\']',
                    r'channels?\.php[^"\']*eid[=:](\d+)',
                ]
                
                for pattern in ajax_patterns:
                    matches = re.findall(pattern, html_text, re.IGNORECASE)
                    if matches:
                        print(f"[Extract]   Found potential AJAX endpoints: {matches[:3]}")
                        # Try calling one
                        for match in matches[:1]:
                            if isinstance(match, str) and 'eid' in match:
                                try:
                                    ajax_url = match if match.startswith('http') else urljoin(event_url, match)
                                    ajax_response = requests.get(ajax_url, headers=HEADERS.copy(), timeout=3, verify=False)
                                    if ajax_response.status_code == 200:
                                        ajax_channels = re.findall(r'[&?]c=(\d{6,7})', ajax_response.text)
                                        if ajax_channels:
                                            found_channels.update(ajax_channels)
                                            print(f"[Extract]     Found {len(ajax_channels)} channels from AJAX endpoint")
                                except:
                                    pass
                
                # Filter to reasonable channel IDs (6-7 digits, in reasonable range)
                valid_channels = [ch for ch in found_channels if len(ch) >= 6 and 100000 <= int(ch) <= 9999999]
                
                print(f"[Extract] Found {len(valid_channels)} potential channel IDs in HTML")
                
                # Also check nested iframe content for channel IDs
                if len(valid_channels) < 8:
                    print(f"[Extract] Checking nested iframes for channel IDs...")
                    for iframe in soup.find_all('iframe')[:5]:  # Check first 5 iframes
                        iframe_src = iframe.get('src', '')
                        if iframe_src and 'livetv' in iframe_src.lower():
                            try:
                                if iframe_src.startswith('//'):
                                    iframe_src = 'https:' + iframe_src
                                elif not iframe_src.startswith('http'):
                                    iframe_src = urljoin(event_url, iframe_src)
                                
                                iframe_headers = HEADERS.copy()
                                iframe_headers['Referer'] = event_url
                                iframe_response = requests.get(iframe_src, headers=iframe_headers, timeout=5, verify=False)
                                iframe_html = iframe_response.text
                                
                                # Search for channel IDs in iframe
                                iframe_channels = re.findall(c_param_pattern, iframe_html)
                                found_channels.update(iframe_channels)
                                valid_channels = [ch for ch in found_channels if len(ch) >= 6 and 100000 <= int(ch) <= 9999999]
                                if iframe_channels:
                                    print(f"[Extract]   Found {len(iframe_channels)} channel IDs in iframe")
                            except:
                                pass
                
                # If we found channel numbers, construct webplayer URLs
                if valid_channels and event_id:
                    # Limit to first 8 channels to match expected count
                    channels_to_use = sorted(valid_channels)[:8]
                    print(f"[Extract] Constructing webplayer URLs for {len(channels_to_use)} channels...")
                    # Known pattern: cdn.livetv869.me/webplayer.php?t=ifr&c={CHANNEL}&lang=en&eid={EID}&lid={CHANNEL}&ci=142&si=27
                    base_url = "https://cdn.livetv869.me/webplayer.php"
                    for channel_id in channels_to_use:
                        webplayer_url = f"{base_url}?t=ifr&c={channel_id}&lang=en&eid={event_id}&lid={channel_id}&ci=142&si=27"
                        # Check if we already have this URL
                        if not any(ch.get('url', '').endswith(f'c={channel_id}&') or f'c={channel_id}&' in ch.get('url', '') for ch in stream_channels):
                            stream_channels.append({
                                'url': webplayer_url,
                                'name': f"Channel {channel_id}",
                                'priority': 0
                            })
                            print(f"[Extract]   Added webplayer URL for Channel {channel_id}")
                    
                    print(f"[Extract] Total webplayer channels now: {len([ch for ch in stream_channels if 'webplayer.php' in ch['url']])}")
        
        # Final fallback: If we still don't have 8 channels and we know the event ID,
        # try fetching a channels endpoint with the event ID
        final_webplayer_count = len([ch for ch in stream_channels if 'webplayer.php' in ch['url']])
        if final_webplayer_count < 8 and event_id:
            # Try alternative API endpoints that might return channel list
            alt_endpoints = [
                f'https://livetv.sx/enx/channels.php?eid={event_id}',
                f'https://cdn.livetv869.me/channels.php?eid={event_id}',
                f'https://livetv.sx/api/getchannels?event_id={event_id}',
            ]
            
            for alt_url in alt_endpoints:
                try:
                    alt_response = requests.get(alt_url, headers=HEADERS.copy(), timeout=3, verify=False)
                    if alt_response.status_code == 200:
                        # Search for webplayer URLs in response
                        webplayer_urls = re.findall(r'https?://[^\s"\'<>]+webplayer\.php[^\s"\'<>]+', alt_response.text)
                        if webplayer_urls:
                            print(f"[Extract] Found {len(webplayer_urls)} webplayer URLs in {alt_url}")
                            for wp_url in webplayer_urls[:8]:
                                channel_match = re.search(r'[&?]c=(\d+)', wp_url)
                                channel_name = f"Channel {channel_match.group(1)}" if channel_match else "Stream Channel"
                                if not any(ch['url'] == wp_url for ch in stream_channels):
                                    stream_channels.append({
                                        'url': wp_url,
                                        'name': channel_name,
                                        'priority': 0
                                    })
                                    print(f"[Extract]   Added webplayer URL: {channel_name}")
                            break
                except:
                    pass
        
        # Sort by priority
        stream_channels.sort(key=lambda x: x['priority'])
        
        # Remove duplicates
        seen_urls = set()
        unique_channels = []
        for channel in stream_channels:
            if channel['url'] not in seen_urls:
                seen_urls.add(channel['url'])
                unique_channels.append(channel)
        
        print(f"[Extract] Found {len(unique_channels)} stream channels to try")
        
        # Try to extract working streams from ALL channels
        for i, channel in enumerate(unique_channels, 1):
            try:
                print(f"[Extract] [{i}/{len(unique_channels)}] Trying {channel['name']}: {channel['url'][:60]}...")
                
                headers_with_ref = HEADERS.copy()
                headers_with_ref['Referer'] = event_url
                
                channel_response = requests.get(channel['url'], headers=headers_with_ref, timeout=10, verify=False)
                print(f"[Extract]   Response: {channel_response.status_code}, Size: {len(channel_response.text)} bytes")
                
                # Look for .m3u8 URLs with multiple patterns
                patterns = [
                    r'source["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'src["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'https?://[^\s"\'\)]+\.m3u8[^\s"\'\)]*',
                    r'["\'](https?://[^"\']*(?:stream|live|hls)[^"\']*\.m3u8[^"\']*)["\']'
                ]
                
                found_stream = False
                for pattern in patterns:
                    m3u8_matches = re.findall(pattern, channel_response.text)
                    if m3u8_matches:
                        for match in m3u8_matches[:3]:  # Try first 3 matches
                            stream_url = match.replace('&amp;', '&')
                            
                            # Less strict verification - accept if URL looks valid
                            if stream_url.startswith('http') and '.m3u8' in stream_url:
                                print(f"[Extract] ✓ Found stream from {channel['name']}: {stream_url[:60]}...")
                                working_streams.append({
                                    'url': stream_url,
                                    'name': channel['name'],
                                    'source_url': channel['url']
                                })
                                found_stream = True
                                break
                        if found_stream:
                            break
                
                # Look for nested iframes and follow them (similar to Rojadirecta)
                nested_soup = BeautifulSoup(channel_response.text, 'html.parser')
                nested_iframes = nested_soup.find_all('iframe')
                
                if nested_iframes:
                    print(f"[Extract]   Found {len(nested_iframes)} nested iframe(s), following them...")
                    
                for nested_iframe in nested_iframes:
                    nested_src = nested_iframe.get('src', '')
                    if nested_src:
                        # Skip malformed PHP URLs
                        if '<?php' in nested_src or 'RU_DOMAIN' in nested_src:
                            continue
                            
                        # Make URL absolute
                        if nested_src.startswith('//'):
                            nested_src = 'https:' + nested_src
                        elif nested_src.startswith('/'):
                            nested_src = urljoin(channel['url'], nested_src)
                        elif not nested_src.startswith('http'):
                            nested_src = urljoin(channel['url'], nested_src)
                        
                        # If it's directly an m3u8, use it
                        if '.m3u8' in nested_src:
                            stream_url = nested_src.replace('&amp;', '&')
                            working_streams.append({
                                'url': stream_url,
                                'name': channel['name'],
                                'source_url': channel['url']
                            })
                            found_stream = True
                            print(f"[Extract]   ✓ Found .m3u8 in iframe: {stream_url[:60]}...")
                            break
                        
                        # Otherwise, follow the nested iframe recursively (up to 3 levels deep)
                        try:
                            print(f"[Extract]   Following nested iframe: {nested_src[:60]}...")
                            nested_headers = HEADERS.copy()
                            nested_headers['Referer'] = channel['url']
                            nested_response = requests.get(nested_src, headers=nested_headers, timeout=10, verify=False)
                            print(f"[Extract]     Response: {nested_response.status_code}, {len(nested_response.text)} bytes")
                            
                            # Look for .m3u8 in nested page
                            for pattern in patterns:
                                m3u8_matches = re.findall(pattern, nested_response.text)
                                if m3u8_matches:
                                    for match in m3u8_matches[:2]:
                                        stream_url = match.replace('&amp;', '&')
                                        if stream_url.startswith('http') and '.m3u8' in stream_url:
                                            print(f"[Extract]   ✓ Found stream in nested iframe: {stream_url[:60]}...")
                                            working_streams.append({
                                                'url': stream_url,
                                                'name': channel['name'],
                                                'source_url': channel['url']
                                            })
                                            found_stream = True
                                            break
                                    if found_stream:
                                        break
                            
                            # If not found, recursively check for deeper iframes (similar to Rojadirecta)
                            if not found_stream:
                                deeper_soup = BeautifulSoup(nested_response.text, 'html.parser')
                                deeper_iframes = deeper_soup.find_all('iframe')
                                
                                for deeper_iframe in deeper_iframes[:3]:  # Limit to 3 deeper levels
                                    deeper_src = deeper_iframe.get('src', '')
                                    if deeper_src:
                                        # Skip malformed URLs
                                        if '<?php' in deeper_src or 'RU_DOMAIN' in deeper_src:
                                            continue
                                        
                                        # Make URL absolute
                                        if deeper_src.startswith('//'):
                                            deeper_src = 'https:' + deeper_src
                                        elif deeper_src.startswith('/'):
                                            deeper_src = urljoin(nested_src, deeper_src)
                                        elif not deeper_src.startswith('http'):
                                            deeper_src = urljoin(nested_src, deeper_src)
                                        
                                        try:
                                            print(f"[Extract]     Following deeper iframe (level 2): {deeper_src[:60]}...")
                                            deeper_response = requests.get(deeper_src, headers=nested_headers, timeout=8, verify=False)
                                            print(f"[Extract]       Response: {deeper_response.status_code}, {len(deeper_response.text)} bytes")
                                            
                                            # Look for .m3u8 in deeper page
                                            for pattern in patterns:
                                                m3u8_matches = re.findall(pattern, deeper_response.text)
                                                if m3u8_matches:
                                                    for match in m3u8_matches[:2]:
                                                        stream_url = match.replace('&amp;', '&')
                                                        if stream_url.startswith('http') and '.m3u8' in stream_url:
                                                            print(f"[Extract]     ✓ Found stream in deeper iframe: {stream_url[:60]}...")
                                                            working_streams.append({
                                                                'url': stream_url,
                                                                'name': channel['name'],
                                                                'source_url': channel['url']
                                                            })
                                                            found_stream = True
                                                            break
                                                    if found_stream:
                                                        break
                                            if found_stream:
                                                break
                                        except Exception as e:
                                            print(f"[Extract]       ✗ Deeper iframe error: {str(e)[:30]}")
                                            continue
                            
                            if found_stream:
                                break
                        except Exception as e:
                            print(f"[Extract]     ✗ Nested iframe error: {str(e)[:40]}")
                            continue
                
                # If no stream found and this is a webplayer.php URL, try Playwright
                if not found_stream and 'webplayer.php' in channel['url'] and PLAYWRIGHT_AVAILABLE:
                    print(f"[Extract]   No stream found, trying Playwright for {channel['name']}...")
                    playwright_streams = extract_stream_with_playwright(channel['url'], channel['name'])
                    if playwright_streams:
                        working_streams.extend(playwright_streams)
                        print(f"[Extract]   ✓ Playwright found {len(playwright_streams)} stream(s)")
                        found_stream = True
                        
            except Exception as e:
                print(f"[Extract]   ✗ Failed: {str(e)[:50]}")
                continue
        
        # If no streams found with regular extraction, try Playwright for JavaScript-loaded streams
        if len(working_streams) == 0 and PLAYWRIGHT_AVAILABLE:
            print(f"[Extract] No streams found with regular extraction, trying Playwright...")
            for i, channel in enumerate(unique_channels[:5], 1):  # Try first 5 channels with Playwright
                if 'webplayer.php' in channel['url']:
                    playwright_streams = extract_stream_with_playwright(channel['url'], channel['name'])
                    if playwright_streams:
                        working_streams.extend(playwright_streams)
                        print(f"[Extract] ✓ Playwright found {len(playwright_streams)} stream(s) from {channel['name']}")
                        break  # Stop after first successful extraction
        
        print(f"[Extract] ✓ Found {len(working_streams)} working stream(s)")
        return working_streams
        
    except Exception as e:
        print(f"[Extract] ✗ Error extracting streams: {e}")
        return []


def extract_stream_with_playwright(webplayer_url, channel_name, timeout=30000, max_popup_closes=15):
    """Extract stream URL using Playwright to execute JavaScript and intercept network requests.
    Handles multiple popup windows that need to be closed repeatedly."""
    if not PLAYWRIGHT_AVAILABLE:
        return []
    
    print(f"[Extract] [Playwright] Extracting from {channel_name}...")
    stream_urls = []
    
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            # Intercept network responses to capture .m3u8 URLs
            def handle_response(response):
                url = response.url
                if '.m3u8' in url.lower():
                    if url not in stream_urls:
                        stream_urls.append(url)
                        print(f"[Extract] [Playwright] ✓ Captured .m3u8 URL: {url[:80]}...")
                # Also check response body for m3u8 URLs
                try:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'text' in content_type or 'json' in content_type:
                            body = response.text()
                            m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                            matches = re.findall(m3u8_pattern, body)
                            for match in matches:
                                if match not in stream_urls and not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ', 'Math.', 'Date.']):
                                    stream_urls.append(match)
                                    print(f"[Extract] [Playwright] ✓ Found .m3u8 in response: {match[:80]}...")
                except:
                    pass
            
            page.on('response', handle_response)
            
            # Navigate to the page
            try:
                page.goto(webplayer_url, wait_until='domcontentloaded', timeout=timeout)
                
                # Wait for initial page load
                page.wait_for_timeout(2000)
                
                # Handle popup overlay div (localpp) - hide it if present
                try:
                    popup_overlay = page.query_selector('#localpp')
                    if popup_overlay:
                        print(f"[Extract] [Playwright] Found popup overlay, hiding it...")
                        # Hide the overlay by setting display to none
                        page.evaluate("""
                            const overlay = document.getElementById('localpp');
                            if (overlay) {
                                overlay.style.display = 'none';
                            }
                        """)
                        page.wait_for_timeout(500)
                except:
                    pass
                
                # Handle multiple popup windows - close them repeatedly
                popup_close_count = 0
                while popup_close_count < max_popup_closes:
                    # Get all pages (main page + popups)
                    all_pages = context.pages
                    
                    if len(all_pages) <= 1:
                        # No popups, break
                        break
                    
                    # Close all popup windows except the main page
                    closed_any = False
                    for popup_page in all_pages:
                        if popup_page != page:
                            try:
                                print(f"[Extract] [Playwright] Closing popup window {popup_close_count + 1}...")
                                popup_page.close()
                                closed_any = True
                                popup_close_count += 1
                            except:
                                pass
                    
                    if not closed_any:
                        break
                    
                    # Wait a bit before checking for more popups
                    page.wait_for_timeout(1000)
                    
                    # Check if popup overlay appeared again and hide it
                    try:
                        popup_overlay = page.query_selector('#localpp')
                        if popup_overlay:
                            page.evaluate("""
                                const overlay = document.getElementById('localpp');
                                if (overlay) {
                                    overlay.style.display = 'none';
                                }
                            """)
                    except:
                        pass
                
                if popup_close_count > 0:
                    print(f"[Extract] [Playwright] ✓ Closed {popup_close_count} popup window(s)")
                
                # Wait for any delayed JavaScript execution after popups are closed
                page.wait_for_timeout(3000)
                
                # Also check the page content for any m3u8 URLs
                page_content = page.content()
                m3u8_pattern = r'https?://[^\s"\'\)<>]+\.m3u8[^\s"\'\)<>]*'
                content_matches = re.findall(m3u8_pattern, page_content)
                for match in content_matches:
                    if match not in stream_urls:
                        # Filter out false positives
                        if not any(js_pattern in match for js_pattern in ['const ', 'function', 'return ', 'Math.', 'Date.']):
                            stream_urls.append(match)
                            print(f"[Extract] [Playwright] ✓ Found .m3u8 in page: {match[:80]}...")
                
            except PlaywrightTimeoutError:
                print(f"[Extract] [Playwright] ⚠ Timeout, but checking captured URLs...")
            
            browser.close()
            
    except Exception as e:
        print(f"[Extract] [Playwright] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    # Convert to the format expected by working_streams
    result = []
    for stream_url in stream_urls:
        result.append({
            'url': stream_url,
            'name': channel_name,
            'source_url': webplayer_url
        })
    
    return result

def extract_stream_from_livetv(event_url):
    """Extract first working stream URL from a LiveTV.sx event page"""
    streams = extract_all_streams_from_livetv(event_url)
    return streams[0]['url'] if streams else None


def search_games(keywords):
    """Search all enabled sources for games matching keywords"""
    all_games = []
    
    # PRIORITY EVENT: Tampa Bay Buccaneers vs New England Patriots (has 10 player links)
    priority_event_id = '314788282'
    
    # Helper function to check if a game URL is the priority event
    # Handles formats: /eventinfo/314788282__/, /eventinfo/314788282_tampa..., eventinfo/314788282
    def is_priority_event(game_url):
        url_lower = game_url.lower()
        # Match event ID in URL - check for /eventinfo/314788282 or eventinfo/314788282
        return f'/eventinfo/{priority_event_id}' in url_lower or f'eventinfo/{priority_event_id}' in url_lower
    
    # Search LiveTV.sx FIRST (highest priority from allupcomingsports/27/)
    livetv_games = search_livetv_games(keywords)
    all_games.extend(livetv_games)
    
    # Search Rojadirecta second
    rojadirecta_games = search_rojadirecta_games(keywords)
    all_games.extend(rojadirecta_games)
    
    # HIGHEST PRIORITY: Always put the specific event with 10 links first
    if len(all_games) > 1:
        priority_games = [g for g in all_games if is_priority_event(g['url'])]
        other_games = [g for g in all_games if not is_priority_event(g['url'])]
        
        if priority_games:
            print(f"[Search] ✓ Found priority event (10 links) - placing first: {priority_games[0].get('title', priority_games[0]['url'])}")
            all_games = priority_games + other_games
        else:
            print(f"[Search] ⚠ Priority event (314788282) not found in search results")
    
    # Sort by: priority event (already first) > source priority (LiveTV.sx first) > match score
    def sort_key(game):
        # Priority event is already first, but keep it in sort key to maintain order
        is_priority = is_priority_event(game['url'])
        source_priority = 0 if game.get('source') == 'LiveTV.sx' else 1
        match_score = game.get('match_score', 0)
        return (-is_priority, source_priority, -match_score)  # Lower priority number = higher priority
    
    all_games.sort(key=sort_key)
    
    print(f"\n✓ Total results: {len(all_games)} (priority event first, then LiveTV.sx prioritized)")
    return all_games


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
        # Try multiple referers - the one we captured from Playwright is https://exposestrat.com/
        # Also try common ones that might work
        referers_to_try = [
            'https://exposestrat.com/',
            'https://arizonaplay.club/',
            'https://livetv.sx/',
            'https://cdn.livetv869.me/'
        ]
        
        response = None
        last_error = None
        
        for referer in referers_to_try:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Referer': referer,
                    'Origin': referer.rstrip('/')
                }
                response = requests.get(current_stream_url, headers=headers, timeout=10, verify=False)
                if response.status_code == 200:
                    break  # Success, use this referer
            except Exception as e:
                last_error = e
                continue
        
        if not response or response.status_code != 200:
            raise Exception(f"Failed to fetch stream with any referer. Last error: {last_error}")
        
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
        
        # Use the same referer strategy for segments
        referers_to_try = [
            'https://exposestrat.com/',
            'https://arizonaplay.club/',
            'https://livetv.sx/',
            'https://cdn.livetv869.me/'
        ]
        
        response = None
        for referer in referers_to_try:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Referer': referer,
                    'Origin': referer.rstrip('/')
                }
                response = requests.get(decoded_url, headers=headers, timeout=10, stream=True, verify=False)
                if response.status_code == 200:
                    break  # Success
            except:
                continue
        
        if not response:
            raise Exception("Failed to fetch segment with any referer")
        
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


@app.route('/api/search')
def api_search():
    """API endpoint to search for games"""
    keywords = request.args.get('q', '')
    
    if not keywords:
        return jsonify({'error': 'No search query provided'}), 400
    
    print(f"\n[API] Searching for: {keywords}")
    games = search_games(keywords)
    
    # Record games in database if they match tracked games
    for game in games:
        if should_track_game(game['title'], game['url']):
            record_game(game['title'], game['url'], game.get('source', 'Unknown'))
            print(f"[Database] 📝 Recorded game: {game['title'][:50]}")
    
    return jsonify({
        'success': True,
        'query': keywords,
        'results': games,
        'count': len(games)
    })


@app.route('/api/load-stream')
def api_load_stream():
    """API endpoint to load a stream from a game URL"""
    game_url = request.args.get('url', '')
    game_title = request.args.get('title', 'Unknown Game')
    
    if not game_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # URL might have encoded hash fragment (%23 instead of #)
    # Decode it to ensure we can parse the hash fragment
    import urllib.parse
    game_url = urllib.parse.unquote(game_url)
    
    print(f"\n[API] Loading stream from: {game_url}")
    if '#' in game_url:
        print(f"[API] URL contains hash fragment: {game_url.split('#', 1)[1]}")
    print(f"[API] Finding ALL available stream channels...")
    
    global current_stream_url, last_refresh_time, stream_info, available_channels, current_channel_index
    
    # Check if this game should be tracked
    should_track = should_track_game(game_title, game_url)
    
    if should_track:
        print(f"[Database] 🏈 Tracking game: {game_title}")
        record_game(game_title, game_url, 'Unknown')
        
        # Check for previously known good links from today
        known_good = get_good_links_for_game(game_url, today_only=True)
        if known_good:
            print(f"[Database] ✓ Found {len(known_good)} known good link(s) from today")
    
    # Get list of bad links to avoid retesting
    bad_links = get_bad_links_for_game(game_url, today_only=True) if should_track else set()
    
    # Extract ALL available streams based on source
    if 'rojadirecta' in game_url.lower() or 'rojadirectame' in game_url.lower():
        print("[API] Detected Rojadirecta source")
        all_streams = extract_all_streams_from_rojadirecta(game_url)
    elif 'livetv.sx' in game_url.lower() or 'livetv872.me' in game_url.lower() or 'livetv' in game_url.lower():
        print("[API] Detected LiveTV source (sx or 872)")
        all_streams = extract_all_streams_from_livetv(game_url)
    else:
        print("[API] Unknown source, trying LiveTV extraction method")
        all_streams = extract_all_streams_from_livetv(game_url)
    
    # If we have known good links, prioritize them
    if should_track and known_good and all_streams:
        # Merge known good links at the top
        known_urls = {g['stream_url'] for g in known_good}
        new_streams = []
        known_streams = []
        
        for stream in all_streams:
            if stream['url'] in known_urls:
                known_streams.append(stream)
            elif stream['url'] not in bad_links:  # Skip known bad links
                new_streams.append(stream)
        
        # Prioritize known good links, then new untested links
        all_streams = known_streams + new_streams
        if known_streams:
            print(f"[Database] ✓ Prioritized {len(known_streams)} known good link(s)")
    
    if all_streams:
        print(f"[API] ✓ Found {len(all_streams)} stream(s)!")
        
        # Test and record link quality for tracked games
        tested_streams = []
        for stream in all_streams:
            stream_url = stream['url']
            
            # Skip known bad links
            if stream_url in bad_links:
                print(f"[Database] ⏭️  Skipping known bad link: {stream_url[:60]}...")
                continue
            
            # Test the link if tracking
            if should_track:
                print(f"[Database] 🧪 Testing link: {stream_url[:60]}...")
                start_time = time.time()
                is_good, error_msg = test_stream_link(stream_url, timeout=5)
                test_duration = time.time() - start_time
                
                record_link_status(
                    game_url=game_url,
                    stream_url=stream_url,
                    channel_name=stream.get('name', 'Unknown'),
                    source_url=stream.get('source_url', game_url),
                    is_good=is_good,
                    error_msg=error_msg,
                    test_duration=test_duration
                )
                
                if is_good:
                    tested_streams.append(stream)
                    print(f"[Database] ✓ Link is GOOD")
                else:
                    # For 503/502 errors, still include the stream - HLS.js might handle it
                    if error_msg and ('503' in str(error_msg) or '502' in str(error_msg)):
                        print(f"[Database] ⚠️  Link returned {error_msg}, but including it anyway (may work in player)")
                        tested_streams.append(stream)
                    else:
                        print(f"[Database] ✗ Link is BAD: {error_msg}")
            else:
                # For non-tracked games, just use the stream
                tested_streams.append(stream)
        
        if not tested_streams:
            # If all tested links were bad, use the first one anyway (user can try)
            print(f"[API] ⚠️  All tested links were bad, using first available")
            tested_streams = [all_streams[0]]
        
        # Store all channels globally (including bad ones for fallback)
        available_channels = all_streams
        current_channel_index = 0
        
        # Use the first good stream, or first available if none tested good
        first_stream = tested_streams[0] if tested_streams else all_streams[0]
        current_stream_url = first_stream['url']
        
        last_refresh_time = datetime.now()
        stream_info = {
            'url': current_stream_url,
            'stream_id': first_stream['name'],
            'last_refresh': last_refresh_time.strftime('%Y-%m-%d %H:%M:%S'),
            'source_url': game_url,
            'channel_name': first_stream['name'],
            'total_channels': len(all_streams),
            'current_channel': 1
        }
        
        print(f"[API] ✓ Loaded {first_stream['name']}: {current_stream_url[:80]}...")
        print(f"[API] ✓ {len(all_streams) - 1} backup channel(s) available")
        
        return jsonify({
            'success': True,
            'stream_url': current_stream_url,
            'proxy_url': '/stream.m3u8',
            'message': f'Stream loaded: {first_stream["name"]}',
            'channel_name': first_stream['name'],
            'total_channels': len(all_streams),
            'current_channel': 1,
            'tested_links': len(tested_streams) if should_track else None
        })
    else:
        print(f"[API] ✗ Failed to extract stream from any available channel")
        available_channels = []
        current_channel_index = 0
        return jsonify({
            'success': False,
            'error': 'Could not extract stream URL from any available channel. The game may not be live or all channels may be offline.'
        }), 404


@app.route('/api/next-channel')
def api_next_channel():
    """API endpoint to skip to the next available channel"""
    global current_stream_url, last_refresh_time, stream_info, available_channels, current_channel_index
    
    if not available_channels:
        return jsonify({
            'success': False,
            'error': 'No channels available. Please load a stream first.'
        }), 400
    
    # Move to next channel (wrap around to start if at end)
    current_channel_index = (current_channel_index + 1) % len(available_channels)
    next_stream = available_channels[current_channel_index]
    
    print(f"\n[API] Switching to channel {current_channel_index + 1}/{len(available_channels)}: {next_stream['name']}")
    
    current_stream_url = next_stream['url']
    last_refresh_time = datetime.now()
    stream_info = {
        'url': current_stream_url,
        'stream_id': next_stream['name'],
        'last_refresh': last_refresh_time.strftime('%Y-%m-%d %H:%M:%S'),
        'source_url': stream_info.get('source_url', ''),
        'channel_name': next_stream['name'],
        'total_channels': len(available_channels),
        'current_channel': current_channel_index + 1
    }
    
    print(f"[API] ✓ Switched to: {current_stream_url[:80]}...")
    
    return jsonify({
        'success': True,
        'stream_url': current_stream_url,
        'proxy_url': '/stream.m3u8',
        'message': f'Switched to {next_stream["name"]}',
        'channel_name': next_stream['name'],
        'total_channels': len(available_channels),
        'current_channel': current_channel_index + 1
    })


@app.route('/api/add-good-link', methods=['POST'])
def api_add_good_link():
    """API endpoint to manually add a good link to the database"""
    data = request.get_json()
    
    game_url = data.get('game_url', '')
    stream_url = data.get('stream_url', '').strip()
    channel_name = data.get('channel_name', 'Manually Added').strip()
    game_title = data.get('game_title', '').strip()
    
    if not stream_url:
        return jsonify({
            'success': False,
            'error': 'Stream URL is required'
        }), 400
    
    if not game_url:
        # Try to use current stream_info if available
        global stream_info
        game_url = stream_info.get('source_url', '')
        if not game_url:
            # If no game URL and no game title provided, use a generic placeholder
            # This allows adding links even when no game is loaded
            if game_title:
                # Create a placeholder game URL based on title
                game_url = f"manual://{game_title.lower().replace(' ', '-')}"
            else:
                game_url = "manual://unknown-game"
    
    print(f"\n[API] Manually adding good link:")
    print(f"  Game: {game_title or 'Unknown'}")
    print(f"  Stream: {stream_url[:80]}...")
    
    # Record the game if title provided (record all manually added games)
    if game_title:
        record_game(game_title, game_url, 'Manual')
    
    # Record the link as good
    record_link_status(
        game_url=game_url,
        stream_url=stream_url,
        channel_name=channel_name or 'Manually Added',
        source_url=game_url,
        is_good=True,
        error_msg=None,
        test_duration=0
    )
    
    print(f"[API] ✓ Added good link to database")
    
    return jsonify({
        'success': True,
        'message': 'Link added as good link',
        'game_url': game_url,
        'stream_url': stream_url
    })


@app.route('/api/links', methods=['GET'])
def api_get_links():
    """API endpoint to get all links for a game"""
    game_url = request.args.get('game_url', '')
    
    if not game_url:
        # Try to use current stream_info if available
        global stream_info
        game_url = stream_info.get('source_url', '')
        if not game_url:
            return jsonify({
                'success': False,
                'error': 'Game URL is required. Please load a game first.'
            }), 400
    
    include_wrong = request.args.get('include_wrong', 'false').lower() == 'true'
    links = get_links_for_game(game_url, include_wrong_game=include_wrong)
    
    return jsonify({
        'success': True,
        'game_url': game_url,
        'links': links,
        'count': len(links)
    })


@app.route('/api/toggle-wrong-game', methods=['POST'])
def api_toggle_wrong_game():
    """API endpoint to toggle wrong_game flag for a link"""
    data = request.get_json()
    
    link_id = data.get('link_id')
    wrong_game = data.get('wrong_game', False)
    
    if link_id is None:
        return jsonify({
            'success': False,
            'error': 'Link ID is required'
        }), 400
    
    success = toggle_wrong_game_flag(link_id, wrong_game)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Link marked as {"wrong game" if wrong_game else "correct game"}'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to update link'
        }), 500


def main():
    print("=" * 60)
    print("🎥 Auto-Refreshing Stream Player")
    print("=" * 60)
    print(f"Main page: {MAIN_PAGE_URL}")
    print(f"Auto-refresh interval: {REFRESH_INTERVAL} seconds")
    print()
    
    # Initialize database
    init_database()
    
    # Check if this is a new day
    new_day = is_new_day()
    if new_day:
        print(f"[Database] 📅 New day detected! ({date.today().strftime('%Y-%m-%d')})")
        print(f"[Database] 🏈 Will track links for: {', '.join(TRACKED_GAMES)}")
        
        # Show database stats
        stats = get_database_stats()
        if stats:
            print(f"[Database] 📊 Stats: {stats.get('total_games', 0)} games, "
                  f"{stats.get('good_today', 0)} good links, {stats.get('bad_today', 0)} bad links today")
    else:
        stats = get_database_stats()
        if stats and stats.get('links_today', 0) > 0:
            print(f"[Database] 📊 Today's stats: {stats.get('good_today', 0)} good, {stats.get('bad_today', 0)} bad links")
    
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

