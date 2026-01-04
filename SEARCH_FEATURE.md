# Search Feature Guide

## Overview
The stream player now includes a powerful search feature that allows you to find live sports games across multiple streaming sites.

## How to Use

### 1. Start the Server
```bash
python3 stream_refresher.py
```

### 2. Open the Player
Navigate to `http://localhost:8080` in your browser.

### 3. Search for Games
At the top of the page, you'll see a search bar. Enter keywords to find games:

**Examples:**
- `barcelona madrid` - Find Barcelona vs Real Madrid matches
- `patriots browns` - Find Patriots vs Browns NFL games
- `lakers warriors` - Find NBA games
- `liverpool chelsea` - Find Premier League matches

### 4. Select a Game
- Search results will appear below the search bar
- Click on any game to load and play it
- The stream will automatically start playing

## Features

### Search Sources
- **LiveTV.sx** - Comprehensive sports streaming directory
- More sources can be added easily

### Smart Matching
- Searches match keywords in game titles
- Results are ranked by relevance
- Shows game time and source

### Automatic Stream Extraction
- Automatically finds the stream URL from the game page
- Extracts .m3u8 HLS streams when available
- Falls back to iframe sources if needed

## API Endpoints

### Search Games
```
GET /api/search?q=barcelona+madrid
```
Returns JSON with matching games.

### Load Stream
```
GET /api/load-stream?url=https://livetv.sx/enx/eventinfo/...
```
Loads a stream from the given event page URL.

## Keyboard Shortcuts
- Press **Enter** in the search box to search
- All standard video controls work normally

## Troubleshooting

### No Results Found
- Try different keywords
- Use team names or player names
- Check if the game is currently live

### Stream Won't Load
- Some games may have complex streaming setups
- Try a different result from the search
- Check the browser console for errors

### Search is Slow
- Initial search may take 5-10 seconds
- Results are scraped in real-time from source sites
- Consider adding more stream sources for redundancy

## Adding More Stream Sources

Edit `stream_refresher.py` and add to the `STREAM_SOURCES` list:

```python
STREAM_SOURCES = [
    {
        'name': 'YourSite',
        'base_url': 'https://example.com',
        'search_url': 'https://example.com/live',
        'enabled': True
    }
]
```

Then implement a search function for that source.

