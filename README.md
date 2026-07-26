Markdown
# OpenStream

OpenStream is a lightweight local media streaming server for browsing and playing movies, TV shows, and IPTV content from devices on the same network. The project combines a Python/FastAPI backend with a Tkinter-based desktop interface so you can point it at a media folder and start streaming quickly.

## What is included

- OpenStreamServer.py: the main server application with a GUI for selecting a library folder and launching the media server.
- library_optimizer.py: a helper tool for optimizing MKV/MP4 files with FFmpeg so they are easier to play on Android devices.
- server.py: a smaller standalone FastAPI example that exposes a catalog over HTTP.

## Features

- Scans folders for video files, thumbnails, and subtitles.
- Serves media over HTTP for local network playback.
- Supports grouped catalogs for movies, series, and IPTV playlists.
- Stores your last-selected media path in ~/.openstream/server_config.json.
- Includes a built-in optimizer for common Android playback issues.

## Requirements

- Python 3.8 or newer
- FFmpeg (required only if you want to use the optimizer tool)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Running the main server

1. Clone the repository:

```bash
git clone https://github.com/donedos/Open_Stream.git
cd Open_Stream
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
python3 OpenStreamServer.py
```

4. In the GUI, click Browse Library, choose your media folder, and click Start Server.

5. Open the displayed local address in your browser or client app, for example:

```text
http://192.168.1.10:8000
```

## Running the optimizer

If you have large MKV/MP4 files that load slowly or have audio issues on Android, you can run the optimizer tool:

```bash
python3 library_optimizer.py
```

Select your media directory and start the process. The tool will use FFmpeg to create optimized files and copy or extract subtitles where possible.

## Expected folder structure

OpenStream scans your selected library for media in a simple, predictable layout. The most reliable format is:

```text
MediaRoot/
├── Movies/
│   └── Action/
│       └── Inception/
│           ├── Inception.mp4
│           ├── Inception.jpg
│           └── Inception.srt
├── Series/
│   └── Drama/
│       └── Breaking Bad/
│           ├── S01E01.mp4
│           ├── S01E01.srt
│           └── poster.jpg
└── IPTV/
    └── channels.m3u
```

Notes:
- Video files should be .mp4, .mkv, .avi, or .webm.
- Thumbnail images can be .jpg, .jpeg, .png, or .webp.
- Subtitle files can be .srt or .vtt.
- For series, placing episodes directly inside a show folder is detected well.

## Project layout

- [OpenStreamServer.py](OpenStreamServer.py) - main desktop app and FastAPI server
- [library_optimizer.py](library_optimizer.py) - media optimization utility
- [server.py](server.py) - simplified FastAPI backend example
- [requirements.txt](requirements.txt) - Python dependencies
- [server_config.json](server_config.json) - saved media path configuration

## Notes

- The application is designed for local-network use and is not intended as a public internet streaming service.
- Some media folders may need companion thumbnail and subtitle files for the best experience.

## License

This project is licensed under the MIT License. See the LICENSE file if present in your distribution.
