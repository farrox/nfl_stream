# 🚀 Quick Start Guide

## Start the Server

```bash
cd /Users/ed/Developer/nfl_stream
./start.sh
```

## Access the Stream

Open your browser to:
```
http://localhost:8080
```

## Check Status

```bash
./check_status.sh
```

## Stop the Server

```bash
pkill -f stream_refresher.py
```

---

## Quick Commands

```bash
# Start
./start.sh

# Status
./check_status.sh

# Open backup streams
./open_backup.sh

# View logs
tail -f server.log
```

---

## Troubleshooting

**Port already in use?**
```bash
lsof -ti:8080 | xargs kill -9
```

**Stream not playing?**
- Click "Force Refresh URL" button
- Or: `curl http://localhost:8080/api/refresh`

**Need help?**
- Read `README.md` for full documentation
- Check `docs/` folder for detailed guides
