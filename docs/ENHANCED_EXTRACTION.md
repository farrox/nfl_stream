# Enhanced Stream Extraction

## What's New

The stream extraction has been **completely rebuilt** to find and try ALL available stream channels, including all backups.

## Key Improvements

### 1. **Multi-Channel Detection**
The system now finds ALL stream channels on a page:
- Direct embedded iframes (highest priority)
- Stream channel buttons (Channel 1, Channel 2, etc.)
- Player links with onclick handlers
- Nested iframe structures

### 2. **Systematic Channel Testing**
For each game, the system will:
```
✓ Find all available channels (typically 5-10 per game)
✓ Try EACH channel systematically
✓ Extract .m3u8 URLs using multiple regex patterns
✓ Verify stream accessibility before returning
✓ Continue to next channel if current fails
```

### 3. **Multiple Extraction Patterns**
The system looks for streams using multiple patterns:
```javascript
source: "https://stream.url/file.m3u8"
file: "https://stream.url/file.m3u8"
src: "https://stream.url/file.m3u8"
https://direct.url/file.m3u8
```

### 4. **Stream Verification**
Before returning a stream URL, the system:
- Makes a HEAD request to verify accessibility
- Checks HTTP status code (< 400 = good)
- Falls back to next channel if verification fails

### 5. **Detailed Logging**
You'll see detailed progress in the console:
```
[Extract] Found 8 stream channels to try
[Extract] [1/8] Trying Channel 1: https://...
[Extract] ✓ SUCCESS! Found .m3u8 stream from Channel 1
[Extract] ✓ Stream verified (HTTP 200)
```

## Example: Patriots vs Browns

For the URL you provided:
`https://livetv.sx/enx/eventinfo/309820300_new_england_patriots_cleveland_browns/`

The system will:
1. **Scrape the page** for all stream channels
2. **Find ~5-10 channels** (Channel 1, Channel 2, HD, SD, etc.)
3. **Try each one** until finding a working .m3u8 stream
4. **Verify** the stream is accessible
5. **Load** the working stream into the player

## How to Use

### From the Web UI:
1. Search for "patriots browns"
2. Click on the game from results
3. Watch the console - you'll see it trying each channel
4. Stream will load automatically when a working one is found

### From the API:
```bash
curl "http://localhost:8080/api/load-stream?url=https://livetv.sx/enx/eventinfo/309820300_new_england_patriots_cleveland_browns/"
```

## Success Rate

The new system dramatically improves success rate because:
- ✅ Tries ALL available channels (not just the first one)
- ✅ Uses multiple extraction patterns
- ✅ Verifies streams before returning
- ✅ Handles nested iframes and JavaScript-loaded players
- ✅ Properly sets referrer headers for each channel

## Fallback Mechanism

If a channel provides an iframe URL instead of direct .m3u8:
1. System fetches the iframe content
2. Searches for .m3u8 URLs in the iframe
3. Extracts and returns the stream
4. If that fails, tries the next channel

## What You'll See in Console

When you load a game, watch the terminal for output like:
```
[API] Loading stream from: https://livetv.sx/enx/eventinfo/...
[API] This will try ALL available stream channels...

[Extract] Fetching event page: https://livetv.sx/...
[Extract] Found 7 stream channels to try

[Extract] [1/7] Trying Channel 1: https://...
[Extract]   ✗ Failed: Connection timeout

[Extract] [2/7] Trying Channel 2: https://...
[Extract] ✓ SUCCESS! Found .m3u8 stream from Channel 2
[Extract]   URL: https://stream.server.com/hls/game.m3u8...
[Extract] ✓ Stream verified (HTTP 200)

[API] ✓ Stream extraction successful!
[API] ✓ Direct .m3u8 stream ready
[API] ✓ Stream loaded: https://stream.server.com/hls/game.m3u8...
```

## Troubleshooting

If all channels fail:
- The game might not be live yet
- All stream providers might be down
- The page structure might have changed
- Check the console for specific error messages

The system will tell you exactly what happened with each channel!
