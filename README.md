# 🎌 KenshinAnime Bot v3.0

Multi-source anime upload & management Telegram bot.

## 🌐 Sources
- 🌊 **AnimeSalt** (animesalt.top)
- 🌍 **AnimeWorld** (watchanimeworld.net)  
- 📋 **AniList** (metadata + auto-track)

## ✨ Features
- `/anime`, `/movie`, `/series` — category search with multi-source results
- Select **ALL seasons** or **ALL episodes** at once
- Select **ALL qualities** (480p → 1080p) — uploads each quality separately
- Custom captions with variables
- Custom thumbnail or AniList poster fallback
- Storage group → auto-forward to channels
- Upload queue with progress bar
- Custom sticker after every episode
- Auto-track new episode alerts
- Multiple admins, broadcast, stats

## 🚀 Deploy

### Heroku
```bash
heroku create
heroku config:set API_ID=... API_HASH=... BOT_TOKEN=...
# (set all .env.example vars)
git push heroku main
heroku ps:scale worker=1
```

### Railway
1. Push to GitHub
2. Connect to Railway → add env vars → Deploy

### Local
```bash
pip install -r requirements.txt
cp .env.example .env  # fill values
python main.py
```

## 📋 All Commands

| Command | Description |
|---|---|
| `/anime <n>` | Search anime (Hindi priority) |
| `/movie <n>` | Search movies |
| `/series <n>` | Search web series |
| `/upload <n>` | Manual upload (send file) |
| `/queue` | Queue status |
| `/add_channel` | Add target channel |
| `/list_channels` | List channels |
| `/remove_channel` | Remove channel |
| `/set_storage <id>` | Set storage group |
| `/set_caption` | Custom caption |
| `/show_caption` | View caption |
| `/reset_caption` | Reset caption |
| `/set_thumbnail` | Set thumbnail |
| `/set_sticker` | Set episode sticker |
| `/set_prefix <text>` | File rename prefix |
| `/add_admin <id>` | Add admin |
| `/remove_admin <id>` | Remove admin |
| `/admins` | List admins |
| `/users` | User stats |
| `/stats` | Upload stats |
| `/broadcast` | Broadcast message |
| `/tracklist` | List tracked anime |
| `/delete_after <s>` | Set delete delay |
| `/help` | All commands |

## 🔄 Upload Flow
```
/anime Solo Leveling
  → 🔍 Search all sources in parallel
  → Select result (shows which sources found it)
  → Select language [⭐ Hindi Dub priority]
  → Select source [AnimeSalt / AnimeWorld]
  → Select season [ALL SEASONS button]
  → Select episode [ALL EPISODES button]
  → Select quality [ALL QUALITIES button]
  → Select target [Channel / This Chat]
  → Queue → Upload each quality → Sticker → Delete
```

## 🎨 Caption Variables
```
{anime_name}  →  Solo Leveling
{season}      →  Season 01
{episode}     →  Episode 05
{audio}       →  Hindi Dub
{quality}     →  1080p
```

## 📁 Structure
```
KenshinBotV2/
├── main.py
├── config.py
├── database.py
├── queue_manager.py
├── auto_track.py
├── handlers/
│   ├── start.py      /start /help
│   ├── search.py     /anime /movie /series
│   ├── upload.py     /upload
│   ├── admin.py      admin commands
│   ├── channels.py   channel management
│   └── broadcast.py  broadcast
├── utils/
│   ├── scrapers/
│   │   ├── base.py       connection pool
│   │   ├── animesalt.py  animesalt.top scraper
│   │   ├── animeworld.py watchanimeworld.net scraper
│   │   ├── anilist.py    AniList API
│   │   └── aggregator.py multi-source merge
│   ├── caption.py
│   ├── downloader.py
│   └── helpers.py
├── requirements.txt
├── Procfile          (Heroku)
├── runtime.txt       (Heroku)
├── app.json          (Heroku)
├── railway.json      (Railway)
└── .env.example
```
