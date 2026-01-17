# 🔧 Git Setup & Push to GitHub

## ⚠️ First: Accept Xcode License

You need to accept the Xcode license before using git:

```bash
sudo xcodebuild -license
```

Then press space to scroll through the license, type "agree" and press Enter.

---

## 📦 Git Setup Commands

After accepting the license, run these commands in order:

### 1. Initialize Git Repository
```bash
cd /Users/ed/Developer/nfl_stream
git init
```

### 2. Add All Files
```bash
git add .
```

### 3. Create Initial Commit
```bash
git commit -m "Initial commit: Auto-refreshing HLS stream proxy server

Features:
- Automatic stream URL extraction from web pages
- Full HTTP proxy with authentication headers
- Auto-refresh system for expiring security tokens
- Web-based HTML5 video player with HLS.js
- Support for 9 backup stream sources
- Background worker for seamless token updates
- Comprehensive documentation (2000+ lines)
- Easy-to-use scripts and tools

Technical Stack:
- Python 3.11 + Flask 3.0
- HLS.js for video playback
- Requests library for HTTP
- Multi-threaded architecture

Includes:
- stream_refresher.py (600+ lines)
- Complete README (1,098 lines)
- Quick start guides
- Backup stream documentation
- Diagnostic and launcher scripts
"
```

### 4. Add Remote Repository
```bash
git remote add origin git@github.com:farrox/nfl_stream.git
```

### 5. Rename Branch to Main
```bash
git branch -M main
```

### 6. Push to GitHub
```bash
git push -u origin main
```

---

## 🔐 SSH Key Setup (If Needed)

If you haven't set up SSH keys for GitHub:

### Check for existing SSH key:
```bash
ls -la ~/.ssh
```

### Generate new SSH key (if needed):
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### Add SSH key to ssh-agent:
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### Copy public key to clipboard:
```bash
cat ~/.ssh/id_ed25519.pub | pbcopy
```

### Add to GitHub:
1. Go to https://github.com/settings/keys
2. Click "New SSH key"
3. Paste your key and save

### Test connection:
```bash
ssh -T git@github.com
```

---

## 📋 Alternative: Using HTTPS

If you prefer HTTPS over SSH:

```bash
git remote remove origin
git remote add origin https://github.com/farrox/nfl_stream.git
git push -u origin main
```

---

## 🚀 Quick Setup (All Commands)

```bash
# Accept Xcode license
sudo xcodebuild -license

# Setup git
cd /Users/ed/Developer/nfl_stream
git init
git add .
git commit -m "Initial commit: Auto-refreshing HLS stream proxy server"

# Add remote and push
git remote add origin git@github.com:farrox/nfl_stream.git
git branch -M main
git push -u origin main
```

---

## 📦 What Will Be Committed

### Core Files
- ✅ stream_refresher.py (Main application)
- ✅ requirements.txt (Dependencies)
- ✅ .gitignore (Exclusions)

### Scripts
- ✅ start.sh (Server launcher)
- ✅ check_status.sh (Diagnostics)
- ✅ open_backup.sh (Backup launcher)
- ✅ run_server.sh (Alternative launcher)

### Documentation
- ✅ README.md (1,098 lines - comprehensive guide)
- ✅ QUICK_START.md (Quick reference)
- ✅ BACKUP_STREAMS.md (Backup documentation)
- ✅ BACKUP_LINKS.md (Backup URLs)
- ✅ PROJECT_SUMMARY.md (Build log)
- ✅ GIT_SETUP.md (This file)

### HTML Files
- ✅ player.html (Standalone player)
- ✅ test_stream.html (Test page)

### Excluded (per .gitignore)
- ❌ server.log (Runtime logs)
- ❌ livetv_page.html (Temp cache)
- ❌ livetv_event.html (Temp cache)
- ❌ __pycache__/ (Python cache)
- ❌ .DS_Store (macOS files)

---

## ✅ Repository Info

**Repository:** nfl_stream  
**Owner:** farrox  
**URL:** https://github.com/farrox/nfl_stream  
**Clone URL (SSH):** git@github.com:farrox/nfl_stream.git  
**Clone URL (HTTPS):** https://github.com/farrox/nfl_stream.git

---

## 📊 Repository Statistics

Once pushed, your repository will contain:
- **~2,820+ lines** of code and documentation
- **15+ files**
- **Multiple languages:** Python, Bash, HTML, CSS, JavaScript
- **Complete working project** with all dependencies

---

## 🎯 After Pushing

1. Visit: https://github.com/farrox/nfl_stream
2. Add repository description
3. Add topics/tags: `python`, `flask`, `hls`, `streaming`, `video-player`, `proxy-server`
4. Consider adding a LICENSE file
5. Update repository settings as needed

---

## 📝 Suggested GitHub Description

```
Auto-refreshing HLS stream proxy server with token management. 
Built with Python + Flask. Features automatic stream extraction, 
full HTTP proxy, and beautiful web player.
```

---

## 🏷️ Suggested Topics

- python
- flask
- hls
- streaming
- video-player
- proxy-server
- nfl
- sports-streaming
- auto-refresh
- web-player

---

**Ready to push your awesome project to GitHub! 🚀**
