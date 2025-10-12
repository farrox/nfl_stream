#!/bin/bash

echo "🎥 NFL Stream - Backup Links"
echo "================================"
echo ""
echo "Your PRIMARY stream is running at: http://localhost:8080"
echo ""
echo "Select a BACKUP stream to open:"
echo ""
echo "1) FlixxLive NFL5"
echo "2) FlixxLive CH6"
echo "3) E2Link Channel"
echo "4) StreamHD247"
echo "5) DovkEmbed CBS"
echo "6) StreamsGate HD-6 (Same as primary)"
echo "7) Backup Channel 7"
echo "8) Backup Channel 8"
echo "9) Backup Channel 9"
echo "0) Open ALL backups in tabs"
echo ""
read -p "Enter choice (0-9): " choice

case $choice in
    1)
        echo "Opening FlixxLive NFL5..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2792166&lang=en&eid=305294497&lid=2792166&ci=142&si=27"
        ;;
    2)
        echo "Opening FlixxLive CH6..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2661179&lang=en&eid=305294497&lid=2661179&ci=142&si=27"
        ;;
    3)
        echo "Opening E2Link..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2843592&lang=en&eid=305294497&lid=2843592&ci=142&si=27"
        ;;
    4)
        echo "Opening StreamHD247..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845145&lang=en&eid=305294497&lid=2845145&ci=142&si=27"
        ;;
    5)
        echo "Opening DovkEmbed CBS..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2847607&lang=en&eid=305294497&lid=2847607&ci=142&si=27"
        ;;
    6)
        echo "Opening StreamsGate (same as primary)..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845115&lang=en&eid=305294497&lid=2845115&ci=142&si=27"
        ;;
    7)
        echo "Opening Backup 7..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2844127&lang=en&eid=305294497&lid=2844127&ci=142&si=27"
        ;;
    8)
        echo "Opening Backup 8..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845062&lang=en&eid=305294497&lid=2845062&ci=142&si=27"
        ;;
    9)
        echo "Opening Backup 9..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2846127&lang=en&eid=305294497&lid=2846127&ci=142&si=27"
        ;;
    0)
        echo "Opening all backup streams..."
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2792166&lang=en&eid=305294497&lid=2792166&ci=142&si=27"
        sleep 1
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2661179&lang=en&eid=305294497&lid=2661179&ci=142&si=27"
        sleep 1
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2843592&lang=en&eid=305294497&lid=2843592&ci=142&si=27"
        sleep 1
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2845145&lang=en&eid=305294497&lid=2845145&ci=142&si=27"
        sleep 1
        open "https://cdn.livetv868.me/webplayer.php?t=ifr&c=2847607&lang=en&eid=305294497&lid=2847607&ci=142&si=27"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Done! Backup stream should be opening in your browser."
echo ""

