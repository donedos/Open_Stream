import os
import re
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Local TV Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your absolute path
BASE_DIR = Path("/home/zed/Videos/stream")
HOST_IP = "192.168.3.59" # Update with the Acer laptop's local IP
PORT = 8000
BASE_URL = f"http://{HOST_IP}:{PORT}"

# Mount the entire stream directory so we can access any file via URL
app.mount("/media", StaticFiles(directory=BASE_DIR), name="media")

def scan_folder_for_assets(folder_path: Path, relative_base: str):
    """Helper to find the video, thumbnail, and subtitle in a specific folder."""
    video_url = None
    thumb_url = None
    sub_url = None
    
    for file in folder_path.iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            rel_path = f"{BASE_URL}/media/{relative_base}/{folder_path.name}/{file.name}"
            
            if ext in [".mp4", ".mkv", ".avi"]:
                video_url = rel_path
            # FIX: Added .webp to the list of supported thumbnail formats
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]: 
                thumb_url = rel_path
            elif ext == ".srt":
                sub_url = rel_path
                
    return video_url, thumb_url, sub_url

def parse_iptv_files(iptv_dir: Path):
    """Scans for M3U, TXT, or JSON playlists and groups channels by category."""
    # We will format this exactly like the Movies dictionary: {"Category": [Channels]}
    grouped_channels = {"Uncategorized": []}
    
    if not iptv_dir.exists():
        return grouped_channels
        
    for file in iptv_dir.iterdir():
        if file.suffix.lower() in [".m3u", ".m3u8"]:
            with open(file, 'r', encoding='utf-8') as f:
                current_name = ""
                current_logo = ""
                current_group = "Uncategorized"
                
                for line in f:
                    line = line.strip()
                    if line.startswith("#EXTINF:"):
                        # Extract Name (Everything after the comma)
                        current_name = line.split(",")[-1].strip()
                        
                        # Extract Logo
                        logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                        current_logo = logo_match.group(1) if logo_match else ""
                        
                        # Extract Group/Category
                        group_match = re.search(r'group-title="([^"]+)"', line)
                        if group_match:
                            current_group = group_match.group(1).strip()
                            if current_group not in grouped_channels:
                                grouped_channels[current_group] = []
                            
                    elif line.startswith("http") and current_name:
                        # Append the channel using the exact same structure as MediaItem
                        grouped_channels[current_group].append({
                            "title": current_name,
                            "video_url": line,
                            "thumbnail_url": current_logo,
                            "subtitle_url": None
                        })
                        current_name = "" # Reset for the next channel
                        
    # Clean up empty Uncategorized if not used
    if not grouped_channels["Uncategorized"]:
        del grouped_channels["Uncategorized"]
        
    return grouped_channels

@app.get("/catalog")
def get_catalog():
    catalog = {
        "movies": {},  # Grouped by Genre
        "series": {},  # Grouped by Genre
        "iptv": []
    }

    # 1. Scan Movies
    movies_dir = BASE_DIR / "movies"
    if movies_dir.exists():
        for genre_folder in movies_dir.iterdir():
            if genre_folder.is_dir():
                genre = genre_folder.name.capitalize()
                catalog["movies"][genre] = []
                
                # Iterate through individual movie folders (e.g., "Die Hard")
                for movie_folder in genre_folder.iterdir():
                    if movie_folder.is_dir():
                        vid, thumb, sub = scan_folder_for_assets(movie_folder, f"movies/{genre_folder.name}")
                        if vid:
                            catalog["movies"][genre].append({
                                "title": movie_folder.name,
                                "video_url": vid,
                                "thumbnail_url": thumb,
                                "subtitle_url": sub
                            })

    # 2. Scan Series (Simplified: Assumes episodes are in the main show folder)
    # 2. Scan Series (Fully Upgraded for Multiple Episodes)
    series_dir = BASE_DIR / "series"
    if series_dir.exists():
        for genre_folder in series_dir.iterdir():
            if genre_folder.is_dir():
                genre = genre_folder.name.capitalize()
                catalog["series"][genre] = {}
                
                # Iterate through shows (e.g., "Breaking Bad", "Cocomelon")
                for show_folder in genre_folder.iterdir():
                    if show_folder.is_dir():
                        show_name = show_folder.name
                        catalog["series"][genre][show_name] = []
                        
                        # Step A: Find the show poster  (any image in the folder)
                        show_thumb = None
                        for file in show_folder.iterdir():
                            if file.is_file() and file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                                show_thumb = f"{BASE_URL}/media/series/{genre_folder.name}/{show_folder.name}/{file.name}"
                                break # Just grab the first image we find to act as the poster
                        
                        # Step B: Find all video episodes
                        for file in show_folder.iterdir():
                            if file.is_file():
                                ext = file.suffix.lower()
                                if ext in [".mp4", ".mkv", ".avi"]:
                                    vid_url = f"{BASE_URL}/media/series/{genre_folder.name}/{show_folder.name}/{file.name}"
                                    
                                    # Look for a matching subtitle with the exact same name (e.g. ep1.mp4 -> ep1.srt)
                                    sub_url = None
                                    sub_file = show_folder / f"{file.stem}.srt"
                                    if sub_file.exists():
                                        sub_url = f"{BASE_URL}/media/series/{genre_folder.name}/{show_folder.name}/{sub_file.name}"

                                    catalog["series"][genre][show_name].append({
                                        "title": file.stem, # Uses the filename (e.g., "S01E01") as the episode title
                                        "video_url": vid_url,
                                        "thumbnail_url": show_thumb,
                                        "subtitle_url": sub_url
                                    })

    # 3. Scan IPTV
    iptv_dir = BASE_DIR / "iptv"
    catalog["iptv"] = parse_iptv_files(iptv_dir)

    return catalog

if __name__ == "__main__":
    import uvicorn
    # Host on 0.0.0.0 so the Android TV can access it over the local network
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)