#!/usr/bin/env python3
"""Quick test of hash fragment parsing logic"""

test_url = "https://livetv872.me/enx/eventinfo/332240466_philadelphia_san_francisco/#webplayer_alieztv|245753|332240466|2914683|142|27|en"

print("Testing Hash Fragment Parsing")
print("="*60)
print(f"URL: {test_url}\n")

# Parse hash fragment
if '#' in test_url:
    hash_part = test_url.split('#', 1)[1]
    print(f"Hash fragment: {hash_part}")
    
    if hash_part.startswith('webplayer_'):
        parts = hash_part.replace('webplayer_', '').split('|')
        print(f"Parts: {parts}")
        
        if len(parts) >= 7:
            params = {
                'provider': parts[0],
                'channel_id': parts[1],
                'event_id': parts[2],
                'lid': parts[3],
                'ci': parts[4],
                'si': parts[5],
                'lang': parts[6]
            }
            
            print("\n✓ Parsed parameters:")
            for key, value in params.items():
                print(f"  {key}: {value}")
            
            # Construct webplayer URL
            webplayer_url = (
                f"https://cdn.livetv872.me/webplayer.php?"
                f"t=ifr&"
                f"c={params['channel_id']}&"
                f"lang={params['lang']}&"
                f"eid={params['event_id']}&"
                f"lid={params['lid']}&"
                f"ci={params['ci']}&"
                f"si={params['si']}"
            )
            
            print(f"\n✓ Constructed webplayer URL:")
            print(f"  {webplayer_url}")
            
            base_url = test_url.split('#')[0]
            print(f"\n✓ Base URL (for referer):")
            print(f"  {base_url}")
            
            print("\n✅ Parsing successful!")
        else:
            print(f"❌ Expected 7 parts, got {len(parts)}")
    else:
        print("❌ Hash doesn't start with 'webplayer_'")
else:
    print("❌ No hash fragment found")
