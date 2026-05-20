import os
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

# --- FASTAPI SERVER SETUP ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Global variables updated dynamically by the GUI
MEDIA_DIR = ""
BASE_URL = ""

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
                            "title": current_name,
                            "video_url": line,
                            "thumbnail_url": current_logo,
                            "subtitle_url": None
                        })
                        current_name = ""
                        
    if not grouped_channels["Uncategorized"]:
        del grouped_channels["Uncategorized"]
        
    return grouped_channels

@app.get("/catalog")
def get_catalog():
    # Convert the dynamic path string from the GUI into a Path object
    base_dir = Path(MEDIA_DIR)
    
    catalog = {
        "movies": {},  
        "series": {},  
        "iptv": {}
    }

    # 1. Scan Movies
    movies_dir = base_dir / "movies"
    if movies_dir.exists():
        for genre_folder in movies_dir.iterdir():
            if genre_folder.is_dir():
                genre = genre_folder.name.capitalize()
                catalog["movies"][genre] = []
                
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

    # 2. Scan Series
    series_dir = base_dir / "series"
    if series_dir.exists():
        for genre_folder in series_dir.iterdir():
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
                                show_thumb = f"{BASE_URL}/media/series/{genre_folder.name}/{show_folder.name}/{file.name}"
                                break 
                        
                        for file in show_folder.iterdir():
                            if file.is_file():
                                ext = file.suffix.lower()
                                if ext in [".mp4", ".mkv", ".avi"]:
                                    vid_url = f"{BASE_URL}/media/series/{genre_folder.name}/{show_folder.name}/{file.name}"
                                    
                                    sub_url = None
                                    sub_file = show_folder / f"{file.stem}.srt"
                                    if sub_file.exists():
                                        sub_url = f"{BASE_URL}/media/series/{genre_folder.name}/{show_folder.name}/{sub_file.name}"

                                    catalog["series"][genre][show_name].append({
                                        "title": file.stem, 
                                        "video_url": vid_url,
                                        "thumbnail_url": show_thumb,
                                        "subtitle_url": sub_url
                                    })

    # 3. Scan IPTV
    iptv_dir = base_dir / "iptv"
    catalog["iptv"] = parse_iptv_files(iptv_dir)

    return catalog


# --- CUSTOM LOG REDIRECTOR ---
class ConsoleRedirector:
    """Catches all print() statements and Uvicorn logs, sending them to the GUI terminal."""
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

        # --- TOP CONTROLS ---
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

        # Start/Status Buttons
        control_frame = tk.Frame(top_frame)
        control_frame.pack(pady=5)
        
        self.status_label = tk.Label(control_frame, text="Status: STOPPED", font=("Arial", 12, "bold"), fg="red", width=15)
        self.status_label.pack(side="left", padx=10)

        self.start_btn = tk.Button(control_frame, text="START SERVER", bg="green", fg="white", font=("Arial", 12, "bold"), command=self.toggle_server, width=15)
        self.start_btn.pack(side="left")

        # --- VS CODE STYLE TERMINAL LOGS ---
        tk.Label(root, text="System Logs:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 2))
        
        self.console = scrolledtext.ScrolledText(root, state='disabled', bg="#1E1E1E", fg="#D4D4D4", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

        sys.stdout = ConsoleRedirector(self.console)
        sys.stderr = ConsoleRedirector(self.console)

        print("[SYSTEM] OpenStream Server GUI Initialized.")
        print(f"[SYSTEM] Ready to host on {self.local_ip}:8000")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            global MEDIA_DIR
            MEDIA_DIR = folder
            print(f"[SETTINGS] Media directory updated to: {MEDIA_DIR}")

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