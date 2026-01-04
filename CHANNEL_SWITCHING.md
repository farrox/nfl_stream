# Channel Switching Feature

## Overview
You can now easily skip between multiple backup stream channels! When you load a game, the system finds ALL working channels and allows you to switch between them with one click.

## How It Works

### 1. **Automatic Channel Detection**
When you load a game, the system:
- Finds ALL available stream channels (typically 5-10 per game)
- Tests each channel to verify it's working
- Stores all working channels for easy switching

### 2. **Switch Anytime**
If the current stream is:
- Laggy or buffering
- Low quality
- Not working properly

Just click the **"⏭️ Next Channel"** button to instantly switch!

## Using the Feature

### From the Web UI

1. **Search for a game**: e.g., "patriots browns"
2. **Click a result** to load the stream
3. **Look for the channel info** bar below the controls:
   ```
   📺 Channel 1 (Channel 1/5) - Click "Next Channel" to switch
   ```
4. **Click "⏭️ Next Channel"** to try the next stream
5. **Keep clicking** to cycle through all available channels

### What You'll See

When a game has multiple channels:
- **Orange "Next Channel" button** appears
- **Channel info bar** shows: `Channel 2/5` (current/total)
- Status shows current channel name
- Button cycles through all channels (wraps to start after last)

### From the API

**Skip to next channel:**
```bash
curl http://localhost:8080/api/next-channel
```

**Response:**
```json
{
  "success": true,
  "channel_name": "Channel 2",
  "current_channel": 2,
  "total_channels": 5,
  "stream_url": "https://...",
  "proxy_url": "/stream.m3u8"
}
```

## Example Workflow

```
1. Search for game → Load Patriots vs Browns
   📺 Channel 1 (Channel 1/5)
   
2. Stream is buffering → Click "Next Channel"
   📺 Channel 2 (Channel 2/5)
   
3. Still laggy → Click "Next Channel"
   📺 Channel 3 (Channel 3/5)
   
4. Perfect! Watch the game 🎉
```

## Features

### ✅ Seamless Switching
- Preserves playback state (playing/paused)
- Minimal interruption
- Automatic playback resume

### ✅ Smart Channel Management
- Only shows working channels
- Cycles through all options
- Wraps around to start

### ✅ Visual Feedback
- Clear channel indicator
- Shows total available channels
- Updates in real-time

## Console Output

When switching channels, you'll see:
```
[API] Switching to channel 2/5: Channel 2
[API] ✓ Switched to: https://stream.url/file.m3u8...
```

## Benefits

### 🎯 **Better Quality**
Try different channels to find the best video quality

### 🚀 **Faster Streams**
Some channels have better bandwidth/servers

### 🔄 **Backup Options**
If one channel goes down, instantly switch to another

### 🎮 **Easy Control**
One-click switching, no need to reload the page

## Tips

1. **Try all channels** - Quality varies between them
2. **Bookmark favorites** - Some channels consistently work better
3. **Switch proactively** - Don't wait for buffering, try a different channel preemptively
4. **Check during halftime** - Load times differ between channels

## Technical Details

- All channels are pre-verified before being made available
- Channel list is stored globally during session
- Switching uses the same proxy mechanism for CORS handling
- Each channel maintains proper referer headers

## Troubleshooting

**No "Next Channel" button?**
- Only one working channel was found
- Game may have limited stream options

**Button shows but doesn't work?**
- Check console for errors
- Try refreshing the page
- Reload the game from search

**All channels buffer?**
- May be an internet connectivity issue
- Try a different game
- Check if streams are live

