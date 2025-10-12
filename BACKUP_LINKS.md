# 🎥 Backup Stream Links
## New Orleans Saints vs New England Patriots

### Currently Running:
✅ **Stream 1 (HDGQ6)** - http://localhost:8080
- Source: `https://streamsgate.live/hd/hd-6.php`
- Status: **ACTIVE** - Keep this running!

---

## 🔄 Backup Links (9 Alternative Streams)

### Link 1
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2661179&lang=en&eid=305294497&lid=2661179&ci=142&si=27
```

### Link 2
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2792166&lang=en&eid=305294497&lid=2792166&ci=142&si=27
```

### Link 3
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2843592&lang=en&eid=305294497&lid=2843592&ci=142&si=27
```

### Link 4
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2844127&lang=en&eid=305294497&lid=2844127&ci=142&si=27
```

### Link 5
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845062&lang=en&eid=305294497&lid=2845062&ci=142&si=27
```

### Link 6 ⭐ (Same as currently running)
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845115&lang=en&eid=305294497&lid=2845115&ci=142&si=27
```

### Link 7
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845145&lang=en&eid=305294497&lid=2845145&ci=142&si=27
```

### Link 8
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2846127&lang=en&eid=305294497&lid=2846127&ci=142&si=27
```

### Link 9
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2847607&lang=en&eid=305294497&lid=2847607&ci=142&si=27
```

---

## 📋 How to Use Backup Links

### Option 1: Open Directly in Browser
Just click any link above to open in a new browser tab.

### Option 2: Extract Stream URL
If a backup link stops working, you can extract the stream URL:

```bash
cd /Users/ed/Developer/streams

# Example: Extract from backup link 2
curl -s "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2792166&lang=en&eid=305294497&lid=2792166&ci=142&si=27" \
  -H "User-Agent: Mozilla/5.0" | grep -i iframe | grep -o 'src="[^"]*"'
```

### Option 3: Use Multi-Stream Script (Coming Soon)
I can create a script that monitors all streams and automatically switches to a backup if the main one fails.

---

## 🔧 Quick Commands

### Check Current Stream Status
```bash
./check_status.sh
```

### View Current Stream URL
```bash
curl http://localhost:8080/api/stream-info
```

### Restart Server
```bash
pkill -f stream_refresher.py && ./start.sh
```

---

## 💡 Stream Quality Tips

Different channels may have:
- Different quality (720p, 1080p, etc.)
- Different reliability
- Different delays (some are more "live" than others)

**Tip:** Test multiple backup links to find the best quality/reliability for you!

---

## ⚠️ Notes

- All these streams are for the same event: **Saints vs Patriots**
- Link 6 (c=2845115) is the one currently running on your server
- These are all from the same source (livetv868.me) but different channels
- If your current stream has issues, try one of these backups!

---

## 🎮 Current Setup

Your server at http://localhost:8080 is:
- ✅ Auto-refreshing every hour
- ✅ Proxying with proper headers
- ✅ Handling 403 errors automatically
- ✅ Running in background

**Keep it running and use these as backups!** 🎉

