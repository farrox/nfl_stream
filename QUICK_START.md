# 🎥 Quick Start Guide

## ✅ Fixed: 403 Forbidden Error

The server now includes a **full proxy** that:
- ✅ Adds proper referrer headers
- ✅ Rewrites M3U8 playlists to proxy all segments
- ✅ Handles CORS properly
- ✅ Bypasses anti-hotlinking protection

---

## 🚀 Start/Restart Server

```bash
cd /Users/ed/Developer/streams
./start.sh
```

Or manually:
```bash
pkill -f stream_refresher.py   # Stop
python stream_refresher.py      # Start
```

---

## 🌐 Access Stream

### Web Browser:
```
http://localhost:8080
```

### From Other Devices on Network:
```
http://192.168.0.249:8080
```

### With Media Players:
```bash
vlc http://localhost:8080/stream.m3u8
mpv http://localhost:8080/stream.m3u8
ffplay http://localhost:8080/stream.m3u8
```

---

## 🔍 Check Status

```bash
./check_status.sh
```

Or manually:
```bash
# Check if running
ps aux | grep stream_refresher

# Check port
lsof -i :8080

# Test API
curl http://localhost:8080/api/stream-info

# View logs
tail -f server.log
```

---

## ⚙️ How It Works

```
1. Python server fetches main page
   ↓
2. Extracts iframe URL
   ↓
3. Fetches stream URL with proper headers
   ↓
4. Proxies M3U8 playlist
   ↓
5. Rewrites segment URLs to use local proxy
   ↓
6. All segments fetched with proper headers
   ↓
7. Video plays in browser! 🎬
```

---

## 📊 Current Stream Info

```bash
# Get current stream URL
curl http://localhost:8080/api/stream-url

# Get full info (JSON)
curl http://localhost:8080/api/stream-info

# Force refresh URL
curl http://localhost:8080/api/refresh
```

---

## 🐛 Troubleshooting

### Stream not playing?
1. Check server is running: `./check_status.sh`
2. Check browser console (F12) for errors
3. Click "Force Refresh URL" button in player
4. Restart server: `pkill -f stream_refresher.py && ./start.sh`

### Port 8080 in use?
Edit `stream_refresher.py` and change:
```python
app.run(host='0.0.0.0', port=8080, debug=False)
```
To:
```python
app.run(host='0.0.0.0', port=9090, debug=False)
```

### Still 403 errors?
The proxy should fix this. Check logs:
```bash
tail -f server.log
```

---

## 💡 Features

- ✅ **Auto-refresh** - Gets new tokens every hour
- ✅ **Full proxy** - Bypasses referrer checks
- ✅ **CORS support** - Works in all browsers
- ✅ **URL rewriting** - Proxies all stream segments
- ✅ **Background worker** - Auto-updates URLs
- ✅ **Web interface** - Beautiful HTML5 player
- ✅ **API endpoints** - Easy integration
- ✅ **Media player support** - Works with VLC/mpv

---

## 📝 Files

- `stream_refresher.py` - Main server
- `start.sh` - Easy launcher
- `check_status.sh` - Status checker
- `server.log` - Server logs
- `requirements.txt` - Dependencies
- `QUICK_START.md` - This file

---

## 🎮 Keyboard Shortcuts in Browser

- `Space` - Play/Pause
- `F` - Fullscreen
- `M` - Mute
- `←/→` - Seek backward/forward

---

## ✨ Success!

Your stream should now be playing at:
**http://localhost:8080** 🎉

