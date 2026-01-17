# 🎥 NFL Stream Backup Links
## New Orleans Saints vs New England Patriots - Oct 12, 2025

---

## ✅ Currently Running (Primary)

**Your Server:** http://localhost:8080
- **Source:** streamsgate.live → azplay.live
- **Stream ID:** HDGQ6
- **Status:** ✅ ACTIVE & Auto-Refreshing
- **Keep this running!**

---

## 🔄 Backup Stream Sources (9 Alternatives)

### Backup 1: FlixxLive NFL5
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2792166&lang=en&eid=305294497&lid=2792166&ci=142&si=27
```
**Stream Source:** `https://flixxlive.pro/live/nfl5_english.php`

---

### Backup 2: FlixxLive CH6
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2661179&lang=en&eid=305294497&lid=2661179&ci=142&si=27
```
**Stream Source:** `https://flixxlive.pro/live/ch6_english.php`

---

### Backup 3: E2Link Channel
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2843592&lang=en&eid=305294497&lid=2843592&ci=142&si=27
```
**Stream Source:** `https://e2link.link/ch.php?id=34`

---

### Backup 4: StreamHD247
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845145&lang=en&eid=305294497&lid=2845145&ci=142&si=27
```
**Stream Source:** `https://streamhd247.world/frame0022.html`

---

### Backup 5: DovkEmbed CBS
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2847607&lang=en&eid=305294497&lid=2847607&ci=142&si=27
```
**Stream Source:** `https://dovkembed.pw/livetv/CBS[USA]`

---

### Backup 6: StreamsGate HD-6 ⭐ (Same as Primary)
```
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845115&lang=en&eid=305294497&lid=2845115&ci=142&si=27
```
**Stream Source:** `https://streamsgate.live/hd/hd-6.php` (Currently Running)

---

### Backup 7-9: Additional Channels
```
Channel ID 2844127:
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2844127&lang=en&eid=305294497&lid=2844127&ci=142&si=27

Channel ID 2845062:
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845062&lang=en&eid=305294497&lid=2845062&ci=142&si=27

Channel ID 2846127:
https://cdn.livetv868.me/webplayer.php?t=ifr&c=2846127&lang=en&eid=305294497&lid=2846127&ci=142&si=27
```

---

## 🎯 Quick Access Links

### Open Backup Streams in Browser:
```bash
# Backup 1 (FlixxLive)
open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2792166&lang=en&eid=305294497&lid=2792166&ci=142&si=27"

# Backup 2 (FlixxLive CH6)
open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2661179&lang=en&eid=305294497&lid=2661179&ci=142&si=27"

# Backup 3 (E2Link)
open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2843592&lang=en&eid=305294497&lid=2843592&ci=142&si=27"

# Backup 4 (StreamHD247)
open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845145&lang=en&eid=305294497&lid=2845145&ci=142&si=27"

# Backup 5 (DovkEmbed)
open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2847607&lang=en&eid=305294497&lid=2847607&ci=142&si=27"
```

---

## 💡 Stream Comparison

| Backup | Source | Pros | Cons |
|--------|--------|------|------|
| **Primary (Running)** | StreamsGate | ✅ Auto-refresh, Proxied | - |
| Backup 1 | FlixxLive NFL5 | Multiple channels | May need testing |
| Backup 2 | FlixxLive CH6 | Same provider | May need testing |
| Backup 3 | E2Link | Different provider | Unknown quality |
| Backup 4 | StreamHD247 | HD quality name | Unknown reliability |
| Backup 5 | DovkEmbed CBS | CBS feed | Unknown quality |

---

## 🚀 How to Use Backups

### Method 1: Direct Browser Access (Easiest)
Just click/open any backup link in your browser.

### Method 2: Extract Direct Stream
```bash
# Example: Get stream URL from backup
curl -s "BACKUP_URL_HERE" | grep -o 'https://[^"]*\.m3u8[^"]*'
```

### Method 3: Add to Your Server (Advanced)
I can help you modify `stream_refresher.py` to support multiple sources with auto-failover!

---

## ⚙️ Multi-Stream Setup (Optional)

Want me to create a version that:
- ✅ Monitors multiple streams simultaneously
- ✅ Auto-switches to backup if primary fails
- ✅ Shows all available streams in the UI
- ✅ Lets you switch between them with one click

Just ask and I'll build it! 🎬

---

## 📊 Current Setup Status

Run this to check your server:
```bash
./check_status.sh
```

Should show:
- ✅ Server Running
- ✅ Port 8080 Listening
- ✅ Stream HDGQ6 Active
- ✅ Next Refresh Scheduled

---

## 🔧 Troubleshooting

### If Primary Stream Stops Working:
1. Click "Force Refresh URL" in the player
2. Check server logs: `tail -f server.log`
3. Try a backup link from above
4. Restart server: `./start.sh`

### If All Streams Have Issues:
- Game might be in commercial break
- Network congestion
- Try different backup sources

---

## 📝 Summary

You have:
- ✅ **1 Primary Stream** running on localhost:8080 (auto-refreshing)
- ✅ **9 Backup Links** from different sources
- ✅ **5 Different Stream Providers** identified
- ✅ **Multiple quality options** to choose from

**Enjoy the game! 🏈**
