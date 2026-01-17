# Test Links for Browser Testing

## Option 1: Direct Webplayer URL (Original Source)
Test the webplayer directly in your browser:
```
https://cdn.livetv869.me/webplayer.php?t=ifr&c=2874403&lang=en&eid=314788282&lid=2874403&ci=142&si=27
```

**What to expect:**
- You'll see the player page
- You may need to close popups multiple times (10+ times)
- The stream should eventually play

---

## Option 2: Flask Server (If Running)
If your Flask server is running on `http://localhost:8080`:

### Main Player Page:
```
http://localhost:8080/
```

### Direct Stream URL (if extracted):
```
http://localhost:8080/stream.m3u8
```

### Search for Games:
```
http://localhost:8080/api/search?q=patriots
```

---

## Option 3: Test the Extracted Stream URL Directly
**Note:** This will likely return 403 Forbidden because it needs the correct referer header.

You can test it, but it won't work without the referer:
```
https://d14.epicquesthero.com:999/hls/mtampabaybuccaneers.m3u8?md5=jeB2ZM34zBXBCf9UrMljiw&expires=1762722054
```

**To make it work:** You'd need to use a browser extension that sets the Referer header to `https://exposestrat.com/`

---

## Recommended Test Flow:

1. **Start the Flask server:**
   ```bash
   python3 stream_refresher.py
   ```

2. **Open in browser:**
   ```
   http://localhost:8080/
   ```

3. **Search for a game:**
   - Use the search box to find "patriots" or "tampa bay"
   - Click on a game result
   - The stream should load automatically

---

## Current Test Webplayer URL:
```
https://cdn.livetv869.me/webplayer.php?t=ifr&c=2874403&lang=en&eid=314788282&lid=2874403&ci=142&si=27
```

This is the Tampa Bay Buccaneers vs New England Patriots game with 10 player links.
