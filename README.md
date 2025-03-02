# PuperBot

## 🎵 Discord Music Bot

A feature-rich Discord music bot that brings your server's music experience to the next level. Stream music from YouTube and Spotify with advanced queue management, playlist support, and lyrics search capabilities.

![Discord Music Bot](https://img.shields.io/badge/Discord-Music%20Bot-7289DA?style=for-the-badge&logo=discord&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)

![YouTube](https://img.shields.io/badge/YouTube-API-red?style=for-the-badge&logo=youtube&logoColor=white) ![Spotify](https://img.shields.io/badge/Spotify-API-1DB954?style=for-the-badge&logo=spotify&logoColor=white) ![Genius](https://img.shields.io/badge/Genius-API-yellow?style=for-the-badge&logo=genius&logoColor=white)

## ✨ Features

- **Multi-Platform Support**: Stream music from YouTube and Spotify (tracks and playlists)
- **Smart Queue Management**: Add songs, play next, view, and shuffle the queue
- **Playlist Integration**: Quick access to predefined playlists through an interactive UI
- **Lyrics Search**: Get song lyrics powered by Genius API
- **User-Friendly Commands**: Simple command structure with a comprehensive help system
- **Voice Channel Intelligence**: Automatically joins user's voice channel and validates commands

## 🔧 Technologies Used

- **Discord.py**: Core framework for bot interaction with Discord API
- **youtube_dl/FFmpeg**: Media streaming and conversion
- **Spotipy**: Spotify API integration for playlist and track handling
- **Genius API**: Lyrics retrieval capabilities
- **asyncio**: Asynchronous programming for efficient operations
- **Custom UI Components**: Interactive playlist selection menus

## 📋 Commands

| Command                  | Description                         |
| ------------------------ | ----------------------------------- |
| `puper pon <url/search>` | Add a song to the queue             |
| `puper ya <url/search>`  | Place a song next in the queue      |
| `puper plists`           | Display playlist selection menu     |
| `puper plists <number>`  | Play specific playlist              |
| `puper queue [page]`     | Show queue contents with pagination |
| `puper lyrics <song>`    | Display lyrics for a song           |
| `puper skip`             | Skip current song                   |
| `puper shuffle`          | Shuffle the queue                   |
| `puper pause/resume`     | Control playback                    |
| `puper stop`             | Stop playback and clear queue       |
| `puper help`             | Display all commands                |

## 🚀 Technical Implementation Highlights

### Asynchronous Architecture

Implemented with asyncio for non-blocking operations, allowing the bot to handle multiple commands simultaneously while streaming audio.

### Smart Media Processing

- Custom YouTube search algorithm to find the best match for user queries
- Spotify playlist extraction with artist and track name parsing
- Efficient file handling with proper naming conventions and format conversion

### User Experience Design

- Context-aware responses with typing indicators
- Interactive UI components for playlist selection
- Paginated queue display for better readability
- Comprehensive error handling with user-friendly messages

### Middleware Implementation

Custom middleware checks to validate user presence in voice channels before executing commands, ensuring proper context for operations.

## 📥 Installation & Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install [FFmpeg](https://ffmpeg.org/download.html) on your system
4. Create a `.env` file with your API keys:
   ```bash
   BOT_TOKEN=your_discord_bot_token
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   GENIUS_TOKEN=your_genius_token
   ```
5. Run the bot:
   ```bash
   python ./puperbot.py
   ```
