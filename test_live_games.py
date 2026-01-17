#!/usr/bin/env python3
"""
Test script to verify live game detection from livetv872.me
"""

import sys
sys.path.insert(0, '.')

from stream_refresher import search_livetv_games, get_live_nfl_games

print("=" * 60)
print("Testing Live Game Detection")
print("=" * 60)

# Test 1: Search for NFL games
print("\n[Test 1] Searching for 'nfl' games...")
nfl_games = search_livetv_games("nfl")
print(f"\nFound {len(nfl_games)} NFL game(s):")
for i, game in enumerate(nfl_games[:10], 1):  # Show first 10
    live_indicator = "🔴 LIVE" if game.get('is_live') else ""
    score = f" (Score: {game.get('score')})" if game.get('score') else ""
    print(f"  {i}. {live_indicator} {game['title']}{score}")
    print(f"     URL: {game['url']}")
    print(f"     Source: {game['source']}")
    print()

# Test 2: Get specifically live games
print("\n[Test 2] Getting live NFL games specifically...")
live_games = get_live_nfl_games()
print(f"\nFound {len(live_games)} live NFL game(s):")
for i, game in enumerate(live_games, 1):
    score = f" (Score: {game.get('score')})" if game.get('score') else ""
    print(f"  {i}. 🔴 LIVE {game['title']}{score}")
    print(f"     URL: {game['url']}")
    print(f"     Source: {game['source']}")
    print()

# Test 3: Search for a specific team
print("\n[Test 3] Searching for 'eagles' games...")
eagles_games = search_livetv_games("eagles")
print(f"\nFound {len(eagles_games)} game(s) matching 'eagles':")
for i, game in enumerate(eagles_games[:5], 1):  # Show first 5
    live_indicator = "🔴 LIVE" if game.get('is_live') else ""
    score = f" (Score: {game.get('score')})" if game.get('score') else ""
    print(f"  {i}. {live_indicator} {game['title']}{score}")
    print(f"     URL: {game['url']}")
    print()

print("=" * 60)
print("Test Complete")
print("=" * 60)
