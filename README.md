Markdown
# 🎬 OpenStream Media Server

OpenStream is a lightweight, blazing-fast, plug-and-play local media server built with Python and FastAPI, paired with a custom Jetpack Compose Android/Android TV client. It turns any local hard drive or external SSD into a fully functional, Netflix-style streaming service for your home network.

**🌍 Cross-Platform:** 100% compatible with macOS, Windows, and Linux!

![OpenStream Preview](https://via.placeholder.com/800x400.png?text=OpenStream+Media+Server) *(Feel free to replace this with an actual screenshot of your Tkinter GUI or Android App!)*

## ✨ Key Features

### 🖥️ The Server (Python / FastAPI)
* **Run Anywhere:** Works seamlessly on macOS, Windows, Ubuntu, Raspberry Pi, or any machine that runs Python.
* **Plug-and-Play GUI:** A sleek, dark-themed Tkinter interface makes hosting accessible. No terminal commands required—just browse for your SSD folder and hit Start.
* **Smart Library Scanner:** Automatically scans your directory, links thumbnails and `.srt` subtitles, and intentionally hides empty folders to keep your client app clean.
* **FastAPI & Uvicorn Engine:** Built on top of modern, async Python frameworks to ensure zero-lag video delivery across your local Wi-Fi.
* **Persistent Memory:** Creates a hidden `~/.openstream/server_config.json` file to remember your exact media path. Perfect for headless auto-booting.
* **Live System Logging:** Monitor network connections, directory scans, and server traffic in real-time directly inside the GUI terminal.

### 🛠️ The MKV Auto-Optimizer (Pro)
* **FFmpeg Integration:** A standalone Tkinter tool (`MKV_Optimizer.py`) that sweeps your library to fix common Android playback issues.
* **Instant Streaming:** Moves the "moov atom" to the front of heavy MP4/MKV files so they load in 1 second instead of 5 minutes.
* **Audio Transcoding:** Converts unplayable DTS/Dolby cinema audio into Android-friendly AAC (`-c:a aac`) while retaining 100% original video quality (`-c:v copy`).
* **Smart Subtitle Extraction:** Automatically copies external `.srt` files or rips embedded subtitles directly from MKV containers for the Android app to read.

### 📱 The Android & TV Client (Jetpack Compose)
* **Seamless Cross-Device UI:** A unified codebase that adapts to both mobile touchscreens and Android TV D-Pad remotes.
* **ExoPlayer Integration:** Hardware-accelerated playback with native support for `TextureView` (fixing sideways portrait videos on TV).
* **Continue Watching:** Remembers your exact playback millisecond. Drop out of a movie and resume it instantly later.
* **Picture-in-Picture (PiP):** Fully integrated Android 12+ PiP with lifecycle-aware audio controls.
* **Smart Hardware Focus:** Advanced Jetpack Compose spatial focus bridges prevent the TV remote from ever getting stuck in empty UI space.

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.8+** installed on your host machine (Mac, Windows, or Linux).
* **FFmpeg** installed (Required *only* if you plan to use the MKV Optimizer).
  * **macOS:** `brew install ffmpeg`
  * **Windows:** Download via `winget install ffmpeg` or from the official site.
  * **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`

### Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/OpenStream.git](https://github.com/yourusername/OpenStream.git)
   cd OpenStream
Install the required Python packages:

Bash
pip install fastapi uvicorn
Usage
Running the Media Server:

Bash
python3 OpenStreamServer.py
(Note: On Windows, you may just need to type python OpenStreamServer.py)

Click Browse Library and select the folder where your movies/shows are stored.

Click Start Server.

The GUI will display your Local IP address (e.g., 192.168.1.X:8000). Point your Android app to this IP!

Running the MKV Optimizer:
If you have heavy MKV files that buffer forever or have no sound on Android:

Bash
python3 MKV_Optimizer.py
Select your media folder.

Click Start. The tool will safely run in the background, processing files without freezing your computer.

💻 Running at Boot (Headless / Auto-Start)
If you compile the server using PyInstaller (pyinstaller --onefile --noconsole OpenStreamServer.py), you can set it to run automatically when your computer turns on.

For Linux (Ubuntu/Debian):

Open your terminal and create a desktop entry:

Bash
nano ~/.config/autostart/openstream.desktop
Paste the following (update the path to match your machine):

Ini, TOML
[Desktop Entry]
Type=Application
Name=OpenStream Server
Comment=Starts the Local Media Server
# Waits 8 seconds to ensure external USB drives are fully mounted!
Exec=bash -c "sleep 8 && /path/to/your/dist/OpenStreamServer"
Terminal=false
X-GNOME-Autostart-enabled=true
For Windows:
Press Win + R, type shell:startup, and drag a shortcut of your compiled .exe into the folder.

For macOS:
Go to System Settings > General > Login Items and add your compiled application to the "Open at Login" list.

🏗️ Built With
FastAPI - Backend API framework

Uvicorn - ASGI web server

Tkinter - Python GUI

Jetpack Compose - Android Native UI

Media3 (ExoPlayer) - Android Video Playback

📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
