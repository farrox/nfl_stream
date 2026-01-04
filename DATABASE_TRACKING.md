# 🗄️ Link Quality Database Tracking

## Overview

The server now automatically tracks good and bad links for specific games (Patriots and Falcons) when running on a new day. This helps prioritize working links and avoid wasting time on broken ones.

## Features

- ✅ **Automatic tracking** for Patriots and Falcons games
- ✅ **New day detection** - detects when server runs on a new day
- ✅ **Link testing** - tests stream URLs for quality
- ✅ **Database storage** - SQLite database stores link quality
- ✅ **Smart prioritization** - good links from today are tried first
- ✅ **Bad link avoidance** - known bad links are skipped

## How It Works

### 1. Database Initialization
When the server starts, it:
- Creates `streams.db` SQLite database if it doesn't exist
- Sets up tables for games and link quality tracking

### 2. New Day Detection
On server startup:
- Checks if this is a new day since last run
- Stores the current date in `.last_run_date` file
- Shows database statistics

### 3. Game Tracking
When searching for games:
- Games matching "patriots" or "falcons" are automatically recorded
- Game information is stored in the database

### 4. Link Testing
When loading a stream for tracked games:
- Extracts all available stream URLs
- Tests each link (quick HTTP request to verify accessibility)
- Records results: **good** (working) or **bad** (broken)
- Prioritizes known good links from today
- Skips known bad links to save time

### 5. Database Schema

**Games Table:**
- `game_name`: Title of the game
- `game_url`: URL of the game page
- `source`: Where the game was found (Rojadirecta, LiveTV.sx, etc.)
- `first_seen_date`: First time this game was seen
- `last_seen_date`: Most recent time this game was seen

**Links Table:**
- `game_url`: Associated game
- `stream_url`: The stream URL (M3U8 link)
- `channel_name`: Name/identifier of the channel
- `source_url`: Where this link was extracted from
- `date_tested`: Date when the link was tested (YYYY-MM-DD)
- `status`: 'good' or 'bad'
- `test_duration`: How long the test took (seconds)
- `error_message`: Error message if link is bad

## Configuration

To track additional games, edit `TRACKED_GAMES` in `stream_refresher.py`:

```python
TRACKED_GAMES = ['patriots', 'falcons']  # Add more here
```

## Database Location

- Database file: `streams.db` (in project root)
- Last run date file: `.last_run_date` (hidden file)

## Example Output

```
[Database] ✓ Initialized database: streams.db
[Database] 📅 New day detected! (2024-01-15)
[Database] 🏈 Will track links for: patriots, falcons
[Database] 📊 Stats: 5 games, 12 good links, 8 bad links today

[API] Loading stream from: https://...
[Database] 🏈 Tracking game: Patriots vs Falcons
[Database] ✓ Found 3 known good link(s) from today
[Database] ✓ Prioritized 3 known good link(s)
[Database] 🧪 Testing link: https://stream.example.com/playlist.m3u8...
[Database] ✓ Link is GOOD
[Database] ✓ Recorded good link: https://stream.example.com/playlist.m3u8...
```

## Benefits

1. **Faster loading** - Known good links are tried first
2. **Less frustration** - Bad links are automatically skipped
3. **Historical data** - Track which links work over time
4. **Daily reset** - Each day starts fresh with new tests

## Database Management

The database is managed automatically, but you can:
- Delete `streams.db` to start fresh
- Delete `.last_run_date` to trigger new day detection
- Database grows over time but links older than 7 days are not prioritized

## Notes

- Link testing has a 5-second timeout
- Only M3U8/stream URLs are tested, not game page URLs
- Testing happens when loading streams, not during search
- Database stats are shown on server startup

