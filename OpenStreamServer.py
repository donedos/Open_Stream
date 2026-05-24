import os
import mimetypes
import sys
import socket
import threading
import json
import tkinter as tk
from tkinter import filedialog, scrolledtext
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import re

# Explicitly teach Python what an MKV file is so it sends the correct content-type header
mimetypes.add_type('video/x-matroska', '.mkv')

# --- FASTAPI SERVER SETUP ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MEDIA_DIR = ""
BASE_URL = ""
#CONFIG_FILE = Path("server_config.json") # File to remember the path
# Create a permanent, hidden settings folder in the user's Home directory
APP_DATA_DIR = Path.home() / ".openstream"
APP_DATA_DIR.mkdir(exist_ok=True) # Creates the folder if it doesn't exist
CONFIG_FILE = APP_DATA_DIR / "server_config.json"

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
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]: 
                thumb_url = rel_path
            elif ext == ".srt":
                sub_url = rel_path
                
    return video_url, thumb_url, sub_url

def parse_iptv_files(iptv_dir: Path):
    """Scans for M3U, TXT, or JSON playlists and groups channels by category."""
    grouped_channels = {"Uncategorized": []}
    if not iptv_dir.exists(): return grouped_channels
    for file in iptv_dir.iterdir():
        if file.suffix.lower() in [".m3u", ".m3u8"]:
            with open(file, 'r', encoding='utf-8') as f:
                current_name, current_logo, current_group = "", "", "Uncategorized"
                for line in f:
                    line = line.strip()
                    if line.startswith("#EXTINF:"):
                        current_name = line.split(",")[-1].strip()
                        logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                        current_logo = logo_match.group(1) if logo_match else ""
                        group_match = re.search(r'group-title="([^"]+)"', line)
                        if group_match:
                            current_group = group_match.group(1).strip()
                            if current_group not in grouped_channels:
                                grouped_channels[current_group] = []
                    elif line.startswith("http") and current_name:
                        grouped_channels[current_group].append({
                            "title": current_name, "video_url": line,
                            "thumbnail_url": current_logo, "subtitle_url": None
                        })
                        current_name = ""
    if not grouped_channels["Uncategorized"]: del grouped_channels["Uncategorized"]
    return grouped_channels

def scan_standard_catalog(catalog_dir: Path, rel_base: str):
    """Dynamically scans any unknown folder for media files."""
    result = {"Uncategorized": []}
    
    # 1. Scan for RAW files dumped directly into this root
    for file in catalog_dir.iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            if ext in [".mp4", ".mkv", ".avi"]:
                vid_url = f"{BASE_URL}/media/{rel_base}/{file.name}"
                thumb_url, sub_url = None, None
                
                # Check for thumb with same name
                for img_ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    thumb_file = catalog_dir / f"{file.stem}{img_ext}"
                    if thumb_file.exists():
                        thumb_url = f"{BASE_URL}/media/{rel_base}/{thumb_file.name}"
                        break
                        
                sub_file = catalog_dir / f"{file.stem}.srt"
                if sub_file.exists():
                    sub_url = f"{BASE_URL}/media/{rel_base}/{sub_file.name}"
                    
                result["Uncategorized"].append({
                    "title": file.stem, "video_url": vid_url,
                    "thumbnail_url": thumb_url, "subtitle_url": sub_url
                })

    # 2. Scan for Subdirectories
    for sub in catalog_dir.iterdir():
        if sub.is_dir():
            has_media = any(f.suffix.lower() in [".mp4", ".mkv", ".avi"] for f in sub.iterdir() if f.is_file())
            
            if has_media:
                vid, thumb, sub_file = scan_folder_for_assets(sub, rel_base)
                if vid:
                    result["Uncategorized"].append({
                        "title": sub.name, "video_url": vid,
                        "thumbnail_url": thumb, "subtitle_url": sub_file
                    })
            else:
                cat_name = sub.name.capitalize()
                result[cat_name] = []
                for media_folder in sub.iterdir():
                    if media_folder.is_dir():
                        vid, thumb, sub_file = scan_folder_for_assets(media_folder, f"{rel_base}/{sub.name}")
                        if vid:
                            result[cat_name].append({
                                "title": media_folder.name, "video_url": vid,
                                "thumbnail_url": thumb, "subtitle_url": sub_file
                            })
                            
    if not result["Uncategorized"]:
        del result["Uncategorized"]
        
    return {k: v for k, v in result.items() if v}

@app.get("/catalog")
def get_catalog():
    base_dir = Path(MEDIA_DIR)
    
    catalog = {
        "catalogs": {},  # The dynamic library
        "series": {},  
        "iptv": {}
    }

    if not base_dir.exists():
        return catalog

    for folder in base_dir.iterdir():
        if folder.is_dir():
            folder_name = folder.name.lower()
            
            if folder_name == "iptv":
                catalog["iptv"] = parse_iptv_files(folder)
                
            elif folder_name in ["series", "tv shows"]:
                for genre_folder in folder.iterdir():
                    if genre_folder.is_dir():
                        genre = genre_folder.name.capitalize()
                        catalog["series"][genre] = {}
                        for show_folder in genre_folder.iterdir():
                            if show_folder.is_dir():
                                show_name = show_folder.name
                                catalog["series"][genre][show_name] = []
                                show_thumb = None
                                for file in show_folder.iterdir():
                                    if file.is_file() and file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                                        show_thumb = f"{BASE_URL}/media/{folder.name}/{genre_folder.name}/{show_folder.name}/{file.name}"
                                        break 
                                for file in show_folder.iterdir():
                                    if file.is_file():
                                        ext = file.suffix.lower()
                                        if ext in [".mp4", ".mkv", ".avi"]:
                                            vid_url = f"{BASE_URL}/media/{folder.name}/{genre_folder.name}/{show_folder.name}/{file.name}"
                                            sub_url = None
                                            sub_file = show_folder / f"{file.stem}.srt"
                                            if sub_file.exists():
                                                sub_url = f"{BASE_URL}/media/{folder.name}/{genre_folder.name}/{show_folder.name}/{sub_file.name}"
                                            catalog["series"][genre][show_name].append({
                                                "title": file.stem, "video_url": vid_url,
                                                "thumbnail_url": show_thumb, "subtitle_url": sub_url
                                            })
            else:
                # Custom dynamic folders (Personal, Anime, Movies, etc)
                scanned_data = scan_standard_catalog(folder, folder.name)
                if scanned_data:
                    catalog["catalogs"][folder.name.capitalize()] = scanned_data

    return catalog


# --- CUSTOM LOG REDIRECTOR ---
class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END) 
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

    def flush(self):
        pass

    def isatty(self):
        return False

# --- GUI AND SERVER THREADING LOGIC ---
class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenStream Media Server")
        self.root.geometry("650x550") 
        self.root.configure(padx=20, pady=20)

        self.server_thread = None
        self.server = None
        self.is_running = False
        self.local_ip = self.get_local_ip()

        top_frame = tk.Frame(root)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="OpenStream Server", font=("Arial", 18, "bold")).pack(pady=(0, 5))
        self.ip_label = tk.Label(top_frame, text=f"Your Server IP: {self.local_ip}", font=("Arial", 12), fg="blue")
        self.ip_label.pack()

        self.folder_var = tk.StringVar(value="No folder selected")
        
        folder_frame = tk.Frame(top_frame)
        folder_frame.pack(fill="x", pady=15)
        tk.Label(folder_frame, text="Media Folder: ", font=("Arial", 10, "bold")).pack(side="left")
        tk.Entry(folder_frame, textvariable=self.folder_var, state="readonly", width=45).pack(side="left", padx=(0, 10))
        tk.Button(folder_frame, text="Browse", command=self.select_folder).pack(side="left")

        control_frame = tk.Frame(top_frame)
        control_frame.pack(pady=5)
        
        self.status_label = tk.Label(control_frame, text="Status: STOPPED", font=("Arial", 12, "bold"), fg="red", width=15)
        self.status_label.pack(side="left", padx=10)

        self.start_btn = tk.Button(control_frame, text="START SERVER", bg="green", fg="white", font=("Arial", 12, "bold"), command=self.toggle_server, width=15)
        self.start_btn.pack(side="left")

        tk.Label(root, text="System Logs:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 2))
        
        self.console = scrolledtext.ScrolledText(root, state='disabled', bg="#1E1E1E", fg="#D4D4D4", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

        sys.stdout = ConsoleRedirector(self.console)
        sys.stderr = ConsoleRedirector(self.console)

        print("[SYSTEM] OpenStream Server GUI Initialized.")
        print(f"[SYSTEM] Ready to host on {self.local_ip}:8000")
        
        # --- NEW AUTO-START LOGIC ---
        # If the saved folder loads successfully, automatically click the start button after 1 second
        if self.load_saved_folder():
            print("[SYSTEM] Valid media folder detected. Auto-starting server in 1 second...")
            self.root.after(1000, self.toggle_server)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def load_saved_folder(self):
        global MEDIA_DIR
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    saved_path = config.get("last_media_dir", "")
                    # Double-check that the path still actually exists on the computer
                    if saved_path and os.path.exists(saved_path):
                        MEDIA_DIR = saved_path
                        self.folder_var.set(saved_path)
                        print(f"[SYSTEM] Automatically restored saved folder: {saved_path}")
                        return True  # Signal that we found a valid folder!
            except Exception as e:
                print(f"[SYSTEM] Failed to read configuration file: {e}")
        return False  # Signal that no valid folder was found

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            global MEDIA_DIR
            MEDIA_DIR = folder
            print(f"[SETTINGS] Media directory updated to: {MEDIA_DIR}")
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump({"last_media_dir": folder}, f)
                print("[SETTINGS] Saved folder selection preference to config file.")
            except Exception as e:
                print(f"[SYSTEM] Failed to write configuration file: {e}")

    def run_uvicorn(self):
        global BASE_URL
        BASE_URL = f"http://{self.local_ip}:8000"
        
        app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
        
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()

    def toggle_server(self):
        if not self.is_running:
            if self.folder_var.get() == "No folder selected":
                print("\n[ERROR] Cannot start server. Please select your media folder first!")
                return

            self.is_running = True
            self.start_btn.config(text="STOP SERVER", bg="red")
            self.status_label.config(text="Status: RUNNING", fg="green")
            
            print("\n" + "="*50)
            print("[INFO] Starting OpenStream Server...")
            print(f"[INFO] Scanning directory: {MEDIA_DIR}")
            print(f"[INFO] Network Access URL: http://{self.local_ip}:8000")
            print("="*50 + "\n")
            
            self.server_thread = threading.Thread(target=self.run_uvicorn, daemon=True)
            self.server_thread.start()
        else:
            print("\n[INFO] Sending stop signal to server. Shutting down...")
            self.is_running = False
            self.start_btn.config(text="START SERVER", bg="green")
            self.status_label.config(text="Status: STOPPED", fg="red")
            if self.server:
                self.server.should_exit = True

if __name__ == "__main__":
    root = tk.Tk()
    app_gui = ServerGUI(root)
    root.mainloop()